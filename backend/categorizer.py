"""Auto-categorization: keyword rules first, then a small ML model (TF-IDF + Logistic Regression)."""
import threading

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from training_data import KEYWORDS, SEED

CONFIDENCE_THRESHOLD = 0.30


class Categorizer:
    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self.train([])

    def train(self, extra_examples):
        """extra_examples: list of (description, category) from user data."""
        texts, labels = [], []
        for cat, examples in SEED.items():
            for e in examples:
                texts.append(e.lower())
                labels.append(cat)
        for desc, cat in extra_examples:
            texts.append(desc.lower())
            labels.append(cat)
        model = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True),
            LogisticRegression(max_iter=1000, C=10.0),
        )
        model.fit(texts, labels)
        with self._lock:
            self._model = model

    def predict(self, description):
        """Returns dict: category, confidence, method."""
        text = (description or "").lower().strip()
        if not text:
            return {"category": "Other", "confidence": 0.0, "method": "default"}

        padded = f" {text} "
        for cat, words in KEYWORDS.items():
            for w in words:
                if w in padded:
                    return {"category": cat, "confidence": 1.0, "method": "rule"}

        with self._lock:
            model = self._model
        probs = model.predict_proba([text])[0]
        best = probs.argmax()
        conf = float(probs[best])
        if conf < CONFIDENCE_THRESHOLD:
            return {"category": "Other", "confidence": conf, "method": "ml-low-confidence"}
        return {"category": str(model.classes_[best]), "confidence": round(conf, 3), "method": "ml"}


categorizer = Categorizer()
