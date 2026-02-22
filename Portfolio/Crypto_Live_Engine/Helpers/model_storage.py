import os
import pickle
from datetime import datetime

class ModelStorage:
    def __init__(self, base_dir='models'):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_model(self, model, model_name, version=None):
        if version is None:
            version = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{model_name}_{version}.pkl"
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, 'wb') as f:
            pickle.dump(model, f)
        print(f" Model saved: {filepath}")
        return filepath

    def load_model(self, model_name, version=None):
        files = [f for f in os.listdir(self.base_dir) if f.startswith(model_name)]
        if not files:
            raise FileNotFoundError(f"No model found with name '{model_name}'")

        # Load latest if version not specified
        if version is None:
            files.sort(reverse=True)
            filename = files[0]
        else:
            filename = f"{model_name}_{version}.pkl"
            if filename not in files:
                raise FileNotFoundError(f"No model found with version '{version}'")

        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, 'rb') as f:
            model = pickle.load(f)
        print(f" Model loaded: {filepath}")
        return model

    def retrain_model(self, model, model_name):
        # Delete existing models with same name
        files = [f for f in os.listdir(self.base_dir) if f.startswith(model_name)]
        for f_name in files:
            filepath = os.path.join(self.base_dir, f_name)
            os.remove(filepath)
            print(f"🗑️ Deleted old model: {filepath}")

        # Save new model
        return self.save_model(model, model_name)


if __name__ == "__main__":
    pass
    #from model_storage import ModelStorage
    #rom sklearn.cluster import KMeans

    # Init
    #storage = ModelStorage()

    # Train new model
    #model = KMeans(n_clusters=3)
    #model.fit([[1, 2], [3, 4], [5, 6]])

    # Retrain & overwrite
    #storage.retrain_model(model, "kmeans_cluster")
