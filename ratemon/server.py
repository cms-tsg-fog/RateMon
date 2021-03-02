import connexion
import logging
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
app = connexion.App(__name__, specification_dir='api/')
CORS(app.app)
app.add_api('ratemon.yaml', base_path="/api/v1")
app.run(port=8085,server='tornado')
