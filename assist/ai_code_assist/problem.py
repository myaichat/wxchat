import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Embedding
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer
import numpy as np

# Sample dataset: Lines of Python code
data = [
    "import numpy as np",
    "import pandas as pd",
    "df = pd.read_csv('data.csv')",
    "print(df.head())",
    "df.describe()",
    "print('Hello, world!')",
    "for i in range(10):",
    "    print(i)"
]

# Tokenizing the code
tokenizer = Tokenizer(char_level=True)
tokenizer.fit_on_text(data)
sequences = tokenizer.texts_to_sequences(data)

# Preparing data for training
X = []
y = []
for sequence in sequences:
    for i in range(1, len(sequence)):
        X.append(sequence[:i])
        y.append(sequence[i])

X = pad_sequences(X, maxlen=50)
y = tf.keras.utils.to_categorical(y, num_classes=len(tokenizer.word_index) + 1)

# Model architecture
model = Sequential([
    Embedding(input_dim=len(tokenizer.word_index) + 1, output_dim=64, input_length=50),
    LSTM(128, return_sequences=False),
    Dense(len(tokenizer.word_index) + 1, activation='softmax')
])

# Compiling the model
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Training the model
model.fit(X, y, epochs=50, verbose=2)

# Function to predict the next character
def predict_next_code(input_text):
    sequence = tokenizer.texts_to_sequences([input_text])
    padded = pad_sequences(sequence, maxlen=50)
    prediction = model.predict(padded)
    idx = np.argmax(prediction)
    return tokenizer.index_word[idx]

# Example usage
input_code = "import pandas as p"
predicted_char = predict_next_code(input_code)
print(f"Next character: {predicted_char}")
