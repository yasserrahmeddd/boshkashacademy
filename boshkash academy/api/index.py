from app import app
import os

# This is the entry point for Vercel
app.debug = False
if __name__ == "__main__":
    app.run()
