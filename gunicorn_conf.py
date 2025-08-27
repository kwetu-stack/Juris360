# gunicorn_conf.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = max(2, multiprocessing.cpu_count() // 2)
timeout = 120
accesslog = "-"
errorlog = "-"
