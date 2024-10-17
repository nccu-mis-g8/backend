import chromadb
 

# 向量資料庫路徑
path = "./chroma"

def init_db_client():
    """初始化資料庫"""
    chroma_client = chromadb.PersistentClient(path=path)
    return chroma_client
 
def create_collection(collection_name):
    """創建collection"""
    chroma_client = init_db_client()
    collection=chroma_client.get_or_create_collection(name=collection_name)
    return collection

def add_document(collection, document, id, metadata):
    """新增單筆資料"""
    collection.add(
        documents=document,
        ids=id,
        metadatas=metadata
    )

def get_all_documents(collection):
    """查詢所有資料"""
    return collection.get()

def get_document(collection, id):
    """查詢單筆資料"""
    return collection.get(id)
    
def update_document(collection, id, document, metadata):
    """更新資料"""
    collection.upsert(
        ids=[id],
        documents=document,
        metadatas=metadata
    )
    
def delete_document(collection, id):
    """刪除資料"""
    collection.delete(id)

def query(collection, query_texts, n_results):
    """檢索資料"""
    return collection.query(
        query_texts=query_texts,
        n_results=n_results
    )

