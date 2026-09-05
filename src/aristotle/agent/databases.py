from concurrent.futures import ThreadPoolExecutor
from aristotle import project_config
from ..graph import GraphDatabase
from ..vector import DocumentationsDatabase

graph_db = GraphDatabase()
docs_db = DocumentationsDatabase()
worker_pool = ThreadPoolExecutor(max_workers=project_config.pool_max_workers)
