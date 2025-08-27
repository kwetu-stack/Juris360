# prestart.py
import app

if __name__ == "__main__":
    # Ensure DB and any seeds run at container boot
    app.init_db()
    app.seed_admin()
    print("Prestart complete.")
