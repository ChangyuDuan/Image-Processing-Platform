import numpy as np
from collections import Counter
import cv2
import json

class DatasetProfiler:
    """数据集整体质量分析器"""
    
    def __init__(self, analysis_results):
        """
        :param analysis_results: List[dict], 包含所有单图 analyze() 的结果
        """
        self.results = analysis_results
        self.total_count = len(analysis_results)
        
    def profile(self):
        """执行五大维度分析"""
        # 即使没有结果也返回默认结构，避免前端报错
        return {
            "integrity": self._analyze_integrity(),
            "rationality": self._analyze_rationality(),
            "purity": self._analyze_purity(),
            "anomaly": self._analyze_anomaly(),
            "diversity": self._analyze_diversity()
        }

    def _analyze_integrity(self):
        """1. 完整性分析"""
        valid_count = sum(1 for r in self.results if r.get("status") == "success")
        error_count = self.total_count - valid_count
        
        # 格式统计
        formats = []
        # 设备来源统计
        cameras = []
        
        for r in self.results:
            if r.get("status") != "success":
                continue
            
            # 假设 filename 后缀作为格式
            ext = r.get("filename", "").split('.')[-1].lower()
            formats.append(ext)
            
            # 提取 EXIF 设备信息
            meta = r.get("data", {}).get("meta_quality", {}).get("exif_info", {})
            model = meta.get("Model", "Unknown")
            cameras.append(model)
            
        return {
            "score": int((valid_count / self.total_count) * 100) if self.total_count > 0 else 0,
            "valid_count": valid_count,
            "error_count": error_count,
            "format_dist": dict(Counter(formats)),
            "camera_dist": dict(Counter(cameras))
        }

    def _analyze_rationality(self):
        """2. 合理性分析 (分布统计)"""
        brightness_list = []
        # 宽高比分类统计：1:1 (Square), 4:3/3:2 (Standard), 16:9/18:9 (Wide), 9:16 (Tall)
        ar_categories = {"Square (1:1)": 0, "Standard (4:3)": 0, "Wide (16:9)": 0, "Tall (9:16)": 0, "Other": 0}
        hue_list = []
        
        width_list = []
        height_list = []
        
        for r in self.results:
            if r.get("status") != "success":
                continue
            data = r.get("data", {})
            
            # 亮度
            b = data.get("color", {}).get("avg_brightness", 0)
            brightness_list.append(b)
            
            # 宽高比分类
            shape = data.get("shape_space", {})
            ar = shape.get("aspect_ratio", 0)
            
            if shape.get("width"):
                width_list.append(shape.get("width"))
            if shape.get("height"):
                height_list.append(shape.get("height"))
                
            if 0.95 <= ar <= 1.05:
                ar_categories["Square (1:1)"] += 1
            elif 1.3 <= ar <= 1.55: # 4:3 ~ 3:2
                ar_categories["Standard (4:3)"] += 1
            elif 1.7 <= ar <= 2.2: # 16:9 ~ 18:9
                ar_categories["Wide (16:9)"] += 1
            elif 0.45 <= ar <= 0.77: # 9:16 ~ 3:4
                ar_categories["Tall (9:16)"] += 1
            else:
                ar_categories["Other"] += 1
            
            # 主色调
            h = data.get("color", {}).get("dominant_hue_value", 0)
            hue_list.append(h)
            
        avg_width = sum(width_list) / len(width_list) if width_list else 0
        avg_height = sum(height_list) / len(height_list) if height_list else 0
        
        max_width = max(width_list) if width_list else 0
        min_width = min(width_list) if width_list else 0
        max_height = max(height_list) if height_list else 0
        min_height = min(height_list) if height_list else 0
            
        return {
            "brightness_dist": np.histogram(brightness_list, bins=10, range=(0, 255))[0].tolist(),
            "aspect_ratio_dist": ar_categories, # 返回分类计数而非原始散点
            "hue_dist": np.histogram(hue_list, bins=12, range=(0, 360))[0].tolist(),
            "avg_width": round(avg_width, 2),
            "avg_height": round(avg_height, 2),
            "max_width": max_width,
            "min_width": min_width,
            "max_height": max_height,
            "min_height": min_height
        }

    def _analyze_purity(self):
        """3. 纯净度分析 (去重)"""
        hashes = {}
        duplicates = []
        
        for r in self.results:
            if r.get("status") != "success":
                continue
                
            phash = r.get("data", {}).get("meta_quality", {}).get("image_phash", "")
            if not phash:
                continue
                
            if phash in hashes:
                duplicates.append({
                    "original": hashes[phash],
                    "duplicate": r.get("filename")
                })
            else:
                hashes[phash] = r.get("filename")
                
        unique_count = len(hashes)
        purity_score = int((unique_count / len(self.results)) * 100) if self.results else 0
        
        return {
            "score": purity_score,
            "duplicate_count": len(duplicates),
            "duplicate_pairs": duplicates[:50] # 只返回前50对
        }

    def _analyze_anomaly(self):
        """4. 异常检测 (找坏图)"""
        anomalies = []
        
        # 简单规则阈值
        for r in self.results:
            if r.get("status") != "success":
                continue
                
            data = r.get("data", {})
            meta = data.get("meta_quality", {})
            color = data.get("color", {})
            
            issues = []
            
            # 模糊检测
            blur = meta.get("blur_score", 1000)
            if blur < 50: # 阈值可调
                issues.append("Blurry")
                
            # 过暗/过曝
            brightness = color.get("avg_brightness", 128)
            if brightness < 10:
                issues.append("Too Dark")
            elif brightness > 245:
                issues.append("Overexposed")
                
            if issues:
                anomalies.append({
                    "filename": r.get("filename"),
                    "issues": issues,
                    "preview_val": blur if "Blurry" in issues else brightness
                })
                
        return {
            "count": len(anomalies),
            "items": anomalies
        }

    def _analyze_diversity(self):
        """5. 多样性分析 (t-SNE 降维)"""
        # 由于 t-SNE 较慢且需要 sklearn，这里暂时用简单的颜色-纹理特征映射代替
        # 如果有 sklearn，可以做真正的 t-SNE
        points = []
        
        for r in self.results:
            if r.get("status") != "success":
                continue
            
            data = r.get("data", {})
            color = data.get("color", {})
            texture = data.get("texture_edge", {})
            
            # 构建一个简单的 3D 特征向量用于展示
            # x: 色调, y: 亮度, z: 纹理对比度
            x = color.get("dominant_hue_value", 0)
            y = color.get("avg_brightness", 0)
            z = texture.get("glcm_contrast", 0)
            
            points.append({
                "name": r.get("filename"),
                "value": [x, y, z]
            })
            
        return {
            "scatter_points": points
        }
