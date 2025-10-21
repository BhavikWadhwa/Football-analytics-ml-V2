import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import joblib
import os


# ----------------------------
# 1. Load the features dataset
# ----------------------------
data_path = os.path.join("data", "features_prematch_full.csv")
df = pd.read_csv(data_path)

print("Loaded dataset with {len(df)} rows and {len(df.columns)} columns")

# ----------------------------
# 2. Select features + target
# ----------------------------
# Basic numeric stats the model can learn from
feature_cols = [
    # team form
    "shots_rolling3", "sog_rolling3", "assists_rolling3",
    "player_count_rolling3", "avg_player_year_rolling3", "win_rate_rolling5",

    # context
    "is_home", "for", "mid",

    # opponent relative form
    "shots_form_diff", "sog_form_diff", "assists_form_diff",
    "player_count_form_diff", "avg_player_year_form_diff", "win_rate_diff"
]


X = df[feature_cols]
y = df["result"]

# Encode result labels (e.g., win/loss/draw)
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Save the label encoder for use in app.py later
os.makedirs("models", exist_ok=True)
joblib.dump(le, "models/label_encoder.pkl")

# ----------------------------
# 3. Train/test split
# ----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

# ----------------------------
# 4. Train the model
# ----------------------------
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    random_state=42
)
model.fit(X_train, y_train)

# ----------------------------
# 5. Evaluate
# ----------------------------
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print("Model Performance:")
print(f"Accuracy: {acc:.3f}")
print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=le.classes_))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))

# ----------------------------
# 6. Save model
# ----------------------------
os.makedirs("models", exist_ok=True)

model_path = os.path.join("models", "random_forest_predictive.pkl")
label_path = os.path.join("models", "label_encoder_predictive.pkl")

joblib.dump(model, model_path)
joblib.dump(le, label_path)

print("Predictive model saved to {model_path}")
print("Label encoder saved to {label_path}")
print("You can now load these in app.py for pre-match prediction.")
