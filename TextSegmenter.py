"""
文本分段器
"""
import config
from typing import List, Union


class TextSegmenter:
    """文本分段器"""
    
    def __init__(self, min_length: int = None, max_length: int = None, 
                 overlap: int = None):
        """
        初始化分段器
        
        Args:
            min_length: 最小分段长度
            max_length: 最大分段长度
            overlap: 重叠长度
        """
        self.min_length = min_length or config.SEGMENT_MIN_LENGTH
        self.max_length = max_length or config.SEGMENT_MAX_LENGTH
        self.overlap = overlap or config.SEGMENT_OVERLAP
        
    def segment_by_structure(self, text: str) -> List[str]:
        """
        按结构分段（章、节、条、款）
        
        Args:
            text: 合同文本
            
        Returns:
            分段列表
        """
        segments = []
        current_segment = []
        lines = text.split('\n')
        
        # 定义结构标记
        structure_markers = ['第', '章', '节', '条', '款', '项', '目', '、']
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是结构标记
            is_structure = any(marker in line for marker in structure_markers)
            
            if is_structure and current_segment:
                # 保存当前段并开始新段
                segment_text = '\n'.join(current_segment)
                if len(segment_text) >= self.min_length:
                    segments.append(segment_text)
                current_segment = [line]
            else:
                current_segment.append(line)
                
        # 处理最后一段
        if current_segment:
            segment_text = '\n'.join(current_segment)
            if len(segment_text) >= self.min_length:
                segments.append(segment_text)
                
        return segments
    
    def segment_by_length(self, text: str) -> List[str]:
        """
        按长度分段（滑动窗口）
        
        Args:
            text: 文本
            
        Returns:
            分段列表
        """
        segments = []
        text_length = len(text)
        
        if text_length <= self.max_length:
            return [text]
            
        start = 0
        while start < text_length:
            end = min(start + self.max_length, text_length)
            
            # 尝试在标点处截断
            if end < text_length:
                for i in range(end, start + self.min_length, -1):
                    if i < text_length and text[i] in '。；.!?；;，,、':
                        end = i + 1
                        break
                        
            segment = text[start:end]
            segments.append(segment)
            
            # 移动窗口，考虑重叠
            start = end - self.overlap
            
        return segments
    
    def smart_segment(self, text: str) -> List[str]:
        """
        智能分段：先尝试按结构分段，如果分段太长再按长度分
        
        Args:
            text: 合同文本
            
        Returns:
            分段列表
        """
        # 先按结构分段
        structure_segments = self.segment_by_structure(text)
        
        final_segments = []
        for segment in structure_segments:
            if len(segment) <= self.max_length:
                final_segments.append(segment)
            else:
                # 按长度进一步分段
                length_segments = self.segment_by_length(segment)
                final_segments.extend(length_segments)
                
        return final_segments
