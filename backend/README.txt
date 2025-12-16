Psoriasis Agent - Final Backend

How to run:
1) cd into the extracted folder and then into backend location:
   python -m pip install -r requirements.txt
   uvicorn main:app --reload

API endpoints (Swagger):
- POST /entry       : create/upsert an entry (provide `psoriasis_flare` 0/1)
- GET  /entries     : list entries
- GET  /summary     : weekly summary (query param weeks=1)
- POST /ml/train    : train ML model (needs >=10 labeled entries)
- GET  /ml/predict  : predict probability of flare for latest entry

Notes:
- DB file (sqlite) psoriasis.db will be created in the backend folder.
- Model is saved as model.pkl in the backend folder.
