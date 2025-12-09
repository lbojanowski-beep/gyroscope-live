git clone https://github.com/lbojanowski-beep/gyroscope-live
cd gyroscope-live

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

export OPENAI_API_KEY="..."
export GYRO_REAL_LLM=1

python -m uvicorn server:app --reload
