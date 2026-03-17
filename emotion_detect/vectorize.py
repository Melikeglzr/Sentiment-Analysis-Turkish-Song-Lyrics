import pandas as pd
import re
import pickle
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# 1. Veriyi Yükle
df = pd.read_csv('labeled_data.csv')

# 2. Metin Temizleme (Küçük harf yapma, noktalama işaretlerini silme)
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

df['clean_lyrics'] = df['lyrics'].apply(clean_text)

# 3. Eğitim ve Test Setine Ayırma
X_train, X_test, y_train, y_test = train_test_split(df['clean_lyrics'], df['emotion'], test_size=0.2, random_state=42)

# 4. Kelimeleri Sayısal Veriye Dönüştürme (TF-IDF)
vectorizer = TfidfVectorizer(max_features=5000)
X_train_vec = vectorizer.fit_transform(X_train)

# 5. Model Eğitimi
model = LogisticRegression(max_iter=1000)
model.fit(X_train_vec, y_train)

# 6. Modeli ve Vectorizer'ı Kaydet (Streamlit'te kullanacağız)
with open('emotion_model.pkl', 'wb') as f:
    pickle.dump(model, f)
with open('tfidf_vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

print("Model başarıyla eğitildi ve kaydedildi! ✨")