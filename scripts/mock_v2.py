"""Run with: python -m scripts.mock_v2 (explicit environment credentials required)."""
from backend.simulation.app import create_app
from backend.simulation.mock import MockEngine
app=create_app(MockEngine())
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8010)
