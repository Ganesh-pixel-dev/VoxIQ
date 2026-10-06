import pandas as pd
import numpy as np
import os

# Create dataset directory
os.makedirs('dataset', exist_ok=True)

# Set random seed for reproducibility
np.random.seed(42)

# Number of samples
num_samples = 1000

# Generating synthetic features
# wpm (words per minute): optimal is ~140. Let's say range 80 - 200
wpm = np.random.normal(loc=140, scale=30, size=num_samples)
wpm = np.clip(wpm, 60, 220)
wpm_diff = np.abs(140 - wpm)

# filler frequency: lower is better (0 to 20)
filler = np.random.exponential(scale=3, size=num_samples)
filler = np.round(np.clip(filler, 0, 25))

# pitch variance: 0 to 2.0 (higher generally better up to a point, say 1.2)
pitch = np.random.normal(loc=1.0, scale=0.4, size=num_samples)
pitch = np.clip(pitch, 0.1, 2.0)

# confidence: 0.0 to 1.0
conf = np.random.beta(a=7, b=3, size=num_samples) # Skewed towards higher confidence

# STAR scores (0.0 to 1.0)
s = np.random.beta(a=5, b=2, size=num_samples)
t = np.random.beta(a=5, b=2, size=num_samples)
a = np.random.beta(a=4, b=3, size=num_samples)
r = np.random.beta(a=3, b=3, size=num_samples) # Result is often forgotten

# keyword relevance: 0.0 to 1.0
kw = np.random.beta(a=4, b=4, size=num_samples)

# Generate target score based on a logical formula + some noise
# Formula weights (approx):
# - wpm_diff: penalty (max penalty around 60 diff -> -15 points)
# - filler: penalty (max penalty around 25 -> -15 points)
# - pitch, conf: positive (up to +10 each)
# - STAR: heavily weighted, 10 points each (up to +40)
# - kw: positive (up to +10)
# Base score: 20

score = 20.0 \
        - (wpm_diff * 0.25) \
        - (filler * 0.6) \
        + (pitch * 5) \
        + (conf * 10) \
        + (s * 10) + (t * 10) + (a * 10) + (r * 10) \
        + (kw * 10)

# Add noise
noise = np.random.normal(0, 3, size=num_samples)
score = score + noise

# Clip score between 0 and 100
score = np.clip(score, 0, 100)

# Create DataFrame
df = pd.DataFrame({
    'wpm': wpm,
    'wpm_diff': wpm_diff,
    'filler_frequency': filler,
    'pitch_variance': pitch,
    'acoustic_confidence': conf,
    'star_s': s,
    'star_t': t,
    'star_a': a,
    'star_r': r,
    'keyword_relevance': kw,
    'interview_score': np.round(score, 1)
})

# Save to CSV
df.to_csv('dataset/interview_data.csv', index=False)
print("Synthetic dataset generated and saved to 'dataset/interview_data.csv'.")
