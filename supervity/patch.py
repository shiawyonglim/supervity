with open('app/routers/data_manager.py', 'a') as f:
    f.write('''
from sqlalchemy import inspect as sqla_inspect

@router.get("/database/tables")
def get_db_tables(db: Session = Depends(get_db)):
    engine = db.get_bind()
    tables = sqla_inspect(engine).get_table_names()
    return {"tables": tables}

@router.get("/database/table/{table_name}")
def get_db_table_data(table_name: str, db: Session = Depends(get_db)):
    engine = db.get_bind()
    tables = sqla_inspect(engine).get_table_names()
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    rows = db.execute(text(f'SELECT * FROM {table_name} LIMIT 100')).mappings().all()
    return {"table": table_name, "rows": [dict(r) for r in rows]}
''')
