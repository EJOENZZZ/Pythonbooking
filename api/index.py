import sys
sys.path.append("..")  # Ensure parent dir is in path for imports
import sys
import traceback
try:
	from app import app as vercel_app
	app = vercel_app
except Exception as e:
	print("Vercel import error:", e, file=sys.stderr)
	traceback.print_exc()
	# Fallback minimal app for error reporting
	from flask import Flask
	app = Flask(__name__)
	@app.route("/")
	def error():
		return f"Vercel import error: {e}", 500
