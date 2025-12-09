"""
向量数据库管理器
"""
import config
from BGEModel import BGEModel
from TextSegmenter import TextSegmenter
from typing import List, Union

class VectorDBManager:
    """向量数据库管理器"""
    
    def __init__(self, persist_directory: str = None):
        """
        初始化向量数据库管理器
        
        Args:
            persist_directory: 数据库存储目录
        """
        import chromadb
        from chromadb.config import Settings
        
        self.persist_directory = persist_directory or config.VECTOR_DB_DIR
        
        # 创建存储目录
        import os
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 初始化BGE模型
        self.bge_model = BGEModel()
        
        # 获取或创建集合
        self.contract_collection = self.client.get_or_create_collection(
            name=config.COLLECTION_CONTRACTS,
            metadata={"description": "合同模板集合"}
        )
        
        self.law_collection = self.client.get_or_create_collection(
            name=config.COLLECTION_LAWS,
            metadata={"description": "法律法规集合"}
        )
        
    def add_contract_template(self, content: str, metadata: dict) -> dict:
        """
        添加合同模板（包含分段处理）
        
        Args:
            content: 合同内容
            metadata: 元数据
            
        Returns:
            包含模板ID和分段ID的字典
        """
        import uuid
        
        # 生成模板ID
        template_id = metadata.get("id") or str(uuid.uuid4())
        
        # 1. 分段处理 TODO
        segments = self.segmenter.smart_segment(content)
        segment_embeddings = self.bge_model.encode_batch(segments)
        segment_ids = []
        
        # 存储分段向量
        for i, (segment, embedding) in enumerate(zip(segments, segment_embeddings)):
            segment_id = f"{template_id}_seg_{i}"
            segment_metadata = metadata.copy()
            segment_metadata.update({
                "template_id": template_id,
                "segment_index": i,
                "segment_count": len(segments)
            })
            
            self.segment_collection.add(
                documents=[segment],
                embeddings=[embedding.tolist()],
                metadatas=[segment_metadata],
                ids=[segment_id]
            )
            segment_ids.append(segment_id)
            
        # 2. 整体合同向量生成（加权平均）
        # 这里可以根据分段的重要性进行加权，简化版本使用简单平均
        if len(segment_embeddings) > 0:
            # 简单平均
            template_embedding = segment_embeddings.mean(axis=0).tolist()
        else:
            # 如果没有分段，直接编码整个文本
            template_embedding = self.bge_model.encode(content).tolist()
            
        # 3. 存储整体模板
        self.contract_collection.add(
            documents=[content],
            embeddings=[template_embedding],
            metadatas=[metadata],
            ids=[template_id]
        )
        
        return {
            "template_id": template_id,
            "segment_ids": segment_ids,
            "segment_count": len(segments),
            "embedding_dim": len(template_embedding)
        }
    
    def add_law_regulation(self, content: str, metadata: dict) -> str:
        """
        添加法律法规
        
        Args:
            content: 法律条文内容
            metadata: 元数据
            
        Returns:
            法规ID
        """
        import uuid
        
        regulation_id = metadata.get("id") or str(uuid.uuid4())
        
        # 生成向量
        embedding = self.bge_model.encode(content).tolist()
        
        # 存储
        self.law_collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[regulation_id]
        )
        
        return regulation_id
    
    def search_with_filter(self, query: str, filter_conditions: dict = None, 
                          collection_name: str = "contracts", n_results: int = 5) -> dict:
        """
        带条件过滤的向量搜索
        
        Args:
            query: 查询文本
            filter_conditions: 过滤条件
            collection_name: 集合名称（contracts/laws/segments）
            n_results: 返回结果数量
            
        Returns:
            搜索结果
        """
        # 获取指定集合
        if collection_name == "contracts":
            collection = self.contract_collection
        elif collection_name == "laws":
            collection = self.law_collection
        elif collection_name == "segments":
            collection = self.segment_collection
        else:
            raise ValueError(f"未知的集合名称: {collection_name}")
            
        # 向量化查询文本
        query_embedding = self.bge_model.encode(query).tolist()
        
        # 构建where条件
        where_conditions = None
        if filter_conditions:
            # 转换过滤条件为ChromaDB格式
            where_conditions = {}
            for key, value in filter_conditions.items():
                if isinstance(value, list):
                    where_conditions[key] = {"$in": value}
                else:
                    where_conditions[key] = value
                    
        # 执行查询
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, 100),
            where=where_conditions,
            include=["documents", "metadatas", "distances", "embeddings"]
        )
        
        return results
    
    def dual_matching(self, user_query: str, user_filters: dict = None) -> dict:
        """
        双重匹配：匹配合同模板和法律法规
        
        Args:
            user_query: 用户查询（自然语言描述）
            user_filters: 用户筛选条件
            
        Returns:
            匹配结果
        """
        # 1. 合同模板匹配
        contract_results = self.search_with_filter(
            query=user_query,
            filter_conditions=user_filters,
            collection_name="contracts",
            n_results=config.MAX_CONTRACT_RESULTS
        )
        
        # 2. 法律法规匹配
        law_results = self.search_with_filter(
            query=user_query,
            filter_conditions=user_filters,
            collection_name="laws",
            n_results=config.MAX_LAW_RESULTS
        )
        
        # 3. 分段匹配（用于细粒度检索）
        segment_results = self.search_with_filter(
            query=user_query,
            filter_conditions=user_filters,
            collection_name="segments",
            n_results=config.MAX_SEGMENT_RESULTS
        )
        
        # 处理结果
        processed_contracts = []
        for i in range(len(contract_results['ids'][0])):
            contract = {
                "id": contract_results['ids'][0][i],
                "content": contract_results['documents'][0][i],
                "metadata": contract_results['metadatas'][0][i],
                "similarity": 1 - contract_results['distances'][0][i],
                "embedding": contract_results['embeddings'][0][i] if contract_results['embeddings'] else None
            }
            processed_contracts.append(contract)
            
        # 按相似度排序
        processed_contracts.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 处理法律法规
        processed_laws = []
        for i in range(len(law_results['ids'][0])):
            law = {
                "id": law_results['ids'][0][i],
                "content": law_results['documents'][0][i],
                "metadata": law_results['metadatas'][0][i],
                "similarity": 1 - law_results['distances'][0][i]
            }
            processed_laws.append(law)
            
        # 过滤低于阈值的法律法规
        processed_laws = [law for law in processed_laws if law["similarity"] >= config.SIMILARITY_THRESHOLD]
        processed_laws.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 处理分段
        processed_segments = []
        for i in range(len(segment_results['ids'][0])):
            segment = {
                "id": segment_results['ids'][0][i],
                "content": segment_results['documents'][0][i],
                "metadata": segment_results['metadatas'][0][i],
                "similarity": 1 - segment_results['distances'][0][i],
                "template_id": segment_results['metadatas'][0][i].get("template_id")
            }
            processed_segments.append(segment)
            
        # 选择最匹配的合同和备用合同
        best_contract = processed_contracts[0] if processed_contracts else None
        alternative_contracts = processed_contracts[1:4] if len(processed_contracts) > 1 else []
        
        return {
            "best_contract": best_contract,
            "alternative_contracts": alternative_contracts,
            "relevant_laws": processed_laws,
            "relevant_segments": processed_segments,
            "query": user_query,
            "filters": user_filters
        }
    