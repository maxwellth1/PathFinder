from pinecone import Pinecone
from openai import OpenAI
import time


pc = Pinecone(
    api_key="pcsk_25Lh7m_64MY6HeGygDtuTRV62eayv8CKudx6QEhHKdbdZDjbuVeHqcVQRKd4qyrmJhezkw"
)

records = [
    {
        "_id": "rec1",
        "How many installments have been collected so far?": "SELECT COUNT(*) FROM basic_emi WHERE installment_count > 0;",
    },
    {
        "_id": "rec2",
        "How many jewellery plans are active?": "SELECT COUNT(*) FROM basic_savingsplan WHERE is_active = 1;",
    },
    {
        "_id": "rec3",
        "How many jewellery plans are paused?": "SELECT COUNT(*) FROM basic_savingsplan WHERE is_paused = 1;",
    },
    {
        "_id": "rec4",
        "How many jewellery plans are completed?": "SELECT COUNT(*) FROM basic_savingsplan WHERE is_completed = 1;",
    },
    {
        "_id": "rec5",
        "How many jewellery plans are Billed?": "SELECT COUNT(*) FROM basic_savingsplan WHERE is_billed = 1",
    },
]

dense_index = pc.Index("zivo-ai-examples")
dense_index.upsert_records("example-namespace", records)


time.sleep(10)

stats = dense_index.describe_index_stats()
print(stats)
