import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops
from skimage.measure import moments_central, moments_hu
import io
from PIL import Image, ExifTags
import imagehash
import onnxruntime as ort
import os

def safe_divide(a, b):
    return float(a) / b if b != 0 else 0.0

def fast_skew_kurtosis(data):
    if data.size == 0:
        return 0.0, 0.0
    
    mean = np.mean(data)
    var = np.var(data)
    
    if var < 1e-10:
        return 0.0, 0.0
        
    std = np.sqrt(var)
    diff = data - mean
    m3 = np.mean(diff ** 3)
    m4 = np.mean(diff ** 4)
    
    skew_val = m3 / (std ** 3)
    kurt_val = m4 / (var ** 2) - 3.0
    
    return float(skew_val), float(kurt_val)

class ImageAnalyzer:
    # 图片特征统计分析器
    _ort_session = None

    def __init__(self, file_content: bytes):
        nparr = np.frombuffer(file_content, np.uint8)
        self.img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        self.file_content = file_content # 保存原始二进制用于PIL读取
        
        if self.img_bgr is None:
            raise ValueError("无法解码图片文件")
            
        self.img_rgb = cv2.cvtColor(self.img_bgr, cv2.COLOR_BGR2RGB)
        self.img_hsv = cv2.cvtColor(self.img_bgr, cv2.COLOR_BGR2HSV)
        self.img_gray = cv2.cvtColor(self.img_bgr, cv2.COLOR_BGR2GRAY)
        
        self.height, self.width = self.img_gray.shape
        max_dim = max(self.height, self.width)
        self.analysis_scale = 1.0
        if max_dim > 1280:
            self.analysis_scale = 1280.0 / max_dim
            self.img_gray_small = cv2.resize(self.img_gray, (0,0), fx=self.analysis_scale, fy=self.analysis_scale)
        else:
            self.img_gray_small = self.img_gray
            
        # 初始化 MobileNet Session (单例模式)
        if ImageAnalyzer._ort_session is None:
            model_path = os.path.join(os.path.dirname(__file__), "mobilenet_v3_small.onnx")
            if os.path.exists(model_path):
                try:
                    ImageAnalyzer._ort_session = ort.InferenceSession(model_path)
                except Exception as e:
                    print(f"Warning: Failed to load ONNX model: {e}")

    def analyze(self):
        return {
            "color": self._analyze_color(),
            "texture_edge": self._analyze_texture_edge(),
            "shape_space": self._analyze_shape_space(),
            "meta_quality": self._analyze_meta_quality(), # 新增维度
            "deep_features": self._extract_deep_features() # 新增维度
        }

    def _analyze_meta_quality(self):
        """分析元数据、清晰度、哈希等质量指标"""
        features = {}
        
        # 1. 模糊度检测 (Laplacian Variance)
        # 方差越小越模糊。一般来说 < 100 可以认为是模糊的
        laplacian_var = cv2.Laplacian(self.img_gray_small, cv2.CV_64F).var()
        features["blur_score"] = float(laplacian_var)
        
        # 2. 感知哈希 (pHash)
        try:
            pil_img = Image.open(io.BytesIO(self.file_content))
            phash = imagehash.phash(pil_img)
            features["image_phash"] = str(phash)
            
            # 3. EXIF 元数据提取
            exif_data = {}
            if hasattr(pil_img, '_getexif') and pil_img._getexif():
                raw_exif = pil_img._getexif()
                for tag, value in raw_exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    if decoded in ['DateTimeOriginal', 'Make', 'Model', 'ISOSpeedRatings', 'ExposureTime', 'FNumber']:
                         # 过滤掉无法序列化的二进制数据
                        if isinstance(value, (str, int, float)):
                            exif_data[decoded] = value
                        elif isinstance(value, tuple):
                             exif_data[decoded] = str(value)
            features["exif_info"] = exif_data
            
        except Exception as e:
            features["image_phash"] = ""
            features["exif_info"] = {}
            print(f"Meta analysis error: {e}")
            
        return features

    def _extract_deep_features(self):
        """使用 MobileNetV3 提取 1024 维语义向量"""
        features = []
        if ImageAnalyzer._ort_session is None:
            return features
            
        try:
            # 预处理: Resize to 224x224, Normalize
            img = cv2.resize(self.img_rgb, (224, 224))
            img = img.astype(np.float32) / 255.0
            img = (img - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
            img = img.transpose(2, 0, 1) # HWC -> CHW
            img = np.expand_dims(img, axis=0) # Add batch dim -> BCHW
            
            # 推理
            input_name = ImageAnalyzer._ort_session.get_inputs()[0].name
            outputs = ImageAnalyzer._ort_session.run(None, {input_name: img})
            
            # MobileNetV3 Small 输出通常是 [1, 576] 或 [1, 1024] 取决于具体层
            # 这里假设提取的是倒数第二层的池化后特征
            embedding = outputs[0].flatten()
            
            # 为了减少传输数据量，我们可以只保留前 128 维 PCA 主成分 (这里简化直接返回前 64 维作为指纹)
            # 或者返回完整的向量用于后续 t-SNE
            features = embedding.tolist()
            
        except Exception as e:
            print(f"Deep feature extraction error: {e}")
            
        return features

    def _analyze_color(self):
        features = {}
        for space_name, img in [("RGB", self.img_rgb), ("HSV", self.img_hsv)]:
            channels = cv2.split(img)
            channel_names = list(space_name) 
            
            for i, c_name in enumerate(channel_names):
                data = channels[i].flatten()
                mean_val = np.mean(data)
                std_val = np.std(data)
                min_val = np.min(data)
                max_val = np.max(data)
                
                features[f"{space_name}_{c_name}_mean"] = float(mean_val)
                features[f"{space_name}_{c_name}_std"] = float(std_val)
                features[f"{space_name}_{c_name}_min"] = float(min_val)
                features[f"{space_name}_{c_name}_max"] = float(max_val)
                step = max(1, len(data) // 10000)
                sample = data[::step]
                
                s_val, k_val = fast_skew_kurtosis(sample)
                
                features[f"{space_name}_{c_name}_skew"] = s_val
                features[f"{space_name}_{c_name}_kurt"] = k_val
        h_hist = cv2.calcHist([self.img_hsv], [0], None, [180], [0, 180])
        dominant_hue_idx = np.argmax(h_hist)
        dominant_hue_ratio = float(h_hist[dominant_hue_idx]) / (self.height * self.width)
        features["dominant_hue_ratio"] = dominant_hue_ratio
        features["dominant_hue_value"] = float(dominant_hue_idx) * 2 
        features["color_hist_h"] = [float(x) for x in h_hist.flatten()[::2]] 
        v_channel = self.img_hsv[:, :, 2]
        features["avg_brightness"] = float(np.mean(v_channel))
        features["brightness_dynamic_range"] = float(np.max(v_channel) - np.min(v_channel))
        v_hist = cv2.calcHist([self.img_hsv], [2], None, [256], [0, 256])
        features["color_hist_v"] = [float(x) for x in v_hist.flatten()[::4]] 
        s_channel = self.img_hsv[:, :, 1]
        features["avg_saturation"] = float(np.mean(s_channel))
        s_hist = cv2.calcHist([self.img_hsv], [1], None, [256], [0, 256])
        features["color_hist_s"] = [float(x) for x in s_hist.flatten()[::4]] 
        features["rgb_boxplot"] = {}
        for i, c_name in enumerate(['R', 'G', 'B']):
            data = self.img_rgb[:, :, i].flatten()
            min_val = float(np.min(data))
            max_val = float(np.max(data))
            if len(data) > 50000:
                step = max(1, len(data) // 50000)
                data = data[::step]
            
            q1, median, q3 = np.percentile(data, [25, 50, 75])
            features["rgb_boxplot"][c_name] = [
                min_val,
                float(q1),
                float(median),
                float(q3),
                max_val
            ]
        if self.height * self.width > 500:
            step = max(1, (self.height * self.width) // 500)
            flat_rgb = self.img_rgb.reshape(-1, 3)
            sampled_rgb = flat_rgb[::step][:500] 
            features["scatter_rgb"] = sampled_rgb.tolist()
        else:
            features["scatter_rgb"] = self.img_rgb.reshape(-1, 3).tolist()
        
        return features

    def _analyze_texture_edge(self):
        features = {}
        scale_glcm = min(1.0, 256.0 / max(self.img_gray_small.shape))
        if scale_glcm < 1.0:
            img_for_glcm = cv2.resize(self.img_gray_small, (0,0), fx=scale_glcm, fy=scale_glcm)
        else:
            img_for_glcm = self.img_gray_small
        img_quantized = (img_for_glcm // 8).astype(np.uint8)
        glcm = graycomatrix(img_quantized, distances=[1], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4], levels=32, symmetric=True, normed=True)
        features["glcm_contrast"] = float(np.mean(graycoprops(glcm, 'contrast')))
        features["glcm_correlation"] = float(np.mean(graycoprops(glcm, 'correlation')))
        features["glcm_energy"] = float(np.mean(graycoprops(glcm, 'energy')))
        features["glcm_homogeneity"] = float(np.mean(graycoprops(glcm, 'homogeneity')))
        edges = cv2.Canny(self.img_gray_small, 100, 200)
        edge_pixel_ratio = float(np.count_nonzero(edges)) / (self.img_gray_small.shape[0] * self.img_gray_small.shape[1])
        features["edge_pixel_ratio"] = edge_pixel_ratio
        gx = cv2.Sobel(self.img_gray_small, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(self.img_gray_small, cv2.CV_32F, 0, 1, ksize=3)
        mag, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        mask = mag > np.mean(mag)
        if np.any(mask):
            valid_angles = angle[mask]
            hist, _ = np.histogram(valid_angles, bins=4, range=(0, 360))
            hist = hist.astype(float) / np.sum(hist)
            features["edge_dir_0_90_ratio"] = float(hist[0])
            features["edge_dir_90_180_ratio"] = float(hist[1])
        else:
            features["edge_dir_0_90_ratio"] = 0.0
            features["edge_dir_90_180_ratio"] = 0.0
        f = np.fft.fft2(self.img_gray_small)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
        
        h, w = magnitude_spectrum.shape
        cy, cx = h//2, w//2
        r = min(h, w) // 4
        mask_low = np.zeros((h, w), np.uint8)
        cv2.circle(mask_low, (cx, cy), r, 1, -1)
        
        total_energy = np.sum(magnitude_spectrum)
        low_freq_energy = np.sum(magnitude_spectrum * mask_low)
        high_freq_energy = total_energy - low_freq_energy
        
        features["fft_low_freq_ratio"] = safe_divide(low_freq_energy, total_energy)
        features["fft_high_freq_ratio"] = safe_divide(high_freq_energy, total_energy)

        return features

    def _analyze_shape_space(self):
        features = {}
        features["height"] = self.height
        features["width"] = self.width
        features["aspect_ratio"] = safe_divide(self.width, self.height)
        _, thresh = cv2.threshold(self.img_gray_small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            cnt = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)
            x, y, w, h = cv2.boundingRect(cnt)
            scale_factor = 1.0 / self.analysis_scale
            features["max_contour_area"] = area * (scale_factor ** 2)
            features["max_contour_perimeter"] = perimeter * scale_factor
            features["max_contour_aspect_ratio"] = safe_divide(w, h)
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                features["center_x_ratio"] = safe_divide(cx, self.img_gray_small.shape[1])
                features["center_y_ratio"] = safe_divide(cy, self.img_gray_small.shape[0])
            else:
                features["center_x_ratio"] = 0.5
                features["center_y_ratio"] = 0.5
        else:
            features["max_contour_area"] = 0
            features["max_contour_perimeter"] = 0
            features["max_contour_aspect_ratio"] = 0
            features["center_x_ratio"] = 0.5
            features["center_y_ratio"] = 0.5
        img_float = self.img_gray_small.astype(np.float32)
        blur = cv2.blur(img_float, (3, 3))
        blur_sq = cv2.sqrBoxFilter(self.img_gray_small, cv2.CV_32F, (3, 3), normalize=True)
        local_var = blur_sq - blur ** 2
        
        features["local_variance_mean"] = float(np.mean(local_var))
        features["local_variance_std"] = float(np.std(local_var))

        return features

def analyze_image_sync(content: bytes, filename: str) -> dict:
    try:
        cv2.setNumThreads(0)
        analyzer = ImageAnalyzer(content)
        features = analyzer.analyze()
        return {
            "filename": filename,
            "status": "success",
            "data": features
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "filename": filename,
            "status": "error",
            "message": str(e)
        }
