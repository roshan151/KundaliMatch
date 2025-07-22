from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import re
from datetime import datetime
import warnings
import os

warnings.filterwarnings('ignore')

app = Flask(__name__)

class MBTIAnalyzer:
    def __init__(self):
        self.classifier = None
        self.vectorizer = None
        self.compatibility_matrix = None
        self.mbti_types = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP',
                          'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']
        self._train_model()
    
    def _create_demo_dataset(self):
        """Create a demo MBTI dataset for training"""
        demo_data = []
        
        # Define personality-appropriate text patterns
        personality_patterns = {
            'I': ["I prefer quiet environments", "I enjoy solitude", "I think before speaking", "I need time alone"],
            'E': ["I love meeting new people", "I enjoy parties", "I feel energized in groups", "I'm social"],
            'N': ["I focus on possibilities", "I like abstract concepts", "I think about the future", "I enjoy theories"],
            'S': ["I focus on details", "I prefer practical information", "I live in the present", "I like concrete facts"],
            'T': ["I make logical decisions", "I analyze objectively", "I value efficiency", "I focus on truth"],
            'F': ["I consider people's feelings", "I value harmony", "I make decisions with heart", "I care about others"],
            'J': ["I like organization", "I prefer structure", "I plan ahead", "I like closure"],
            'P': ["I'm flexible", "I adapt easily", "I keep options open", "I'm spontaneous"]
        }
        
        for i in range(2000):  # Create 2000 demo users for better training
            mbti_type = np.random.choice(self.mbti_types)
            
            # Generate personality-appropriate text
            posts = []
            for dimension in mbti_type:
                posts.extend(np.random.choice(personality_patterns[dimension], size=2))
            
            # Add some variation
            if 'NT' in mbti_type:
                posts.append("I enjoy intellectual discussions and complex problems")
            elif 'NF' in mbti_type:
                posts.append("I care about personal growth and helping others")
            elif 'ST' in mbti_type:
                posts.append("I focus on practical solutions and efficiency")
            elif 'SF' in mbti_type:
                posts.append("I value relationships and helping people")
            
            combined_posts = ". ".join(posts)
            demo_data.append({'type': mbti_type, 'posts': combined_posts})
        
        return pd.DataFrame(demo_data)
    
    def _preprocess_text(self, text):
        """Preprocess text for analysis"""
        # Remove URLs, mentions, and special characters
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        text = text.lower().strip()
        return text
    
    def _create_compatibility_matrix(self):
        """Create MBTI compatibility matrix"""
        # Create compatibility matrix (60-95 scale)
        compatibility_matrix = np.random.randint(60, 95, size=(16, 16))
        
        # Set golden pairs (highest compatibility)
        golden_pairs = {
            'INTJ': ['ENFP', 'ENTP'],
            'INTP': ['ENFJ', 'ENTJ'],
            'ENTJ': ['INFP', 'INTP'],
            'ENTP': ['INFJ', 'INTJ'],
            'INFJ': ['ENFP', 'ENTP'],
            'INFP': ['ENFJ', 'ENTJ'],
            'ENFJ': ['INFP', 'INTP'],
            'ENFP': ['INFJ', 'INTJ'],
            'ISTJ': ['ESFP', 'ESTP'],
            'ISFJ': ['ESFP', 'ESTP'],
            'ESTJ': ['ISFP', 'ISTP'],
            'ESFJ': ['ISFP', 'ISTP'],
            'ISTP': ['ESFJ', 'ESTJ'],
            'ISFP': ['ESFJ', 'ESTJ'],
            'ESTP': ['ISFJ', 'ISTJ'],
            'ESFP': ['ISFJ', 'ISTJ']
        }
        
        # Update matrix with golden pairs
        for i, type1 in enumerate(self.mbti_types):
            for j, type2 in enumerate(self.mbti_types):
                if type2 in golden_pairs.get(type1, []):
                    compatibility_matrix[i][j] = np.random.randint(90, 100)
                elif type1 == type2:
                    compatibility_matrix[i][j] = np.random.randint(75, 85)
        
        return pd.DataFrame(compatibility_matrix, index=self.mbti_types, columns=self.mbti_types)
    
    def _train_model(self):
        """Train the MBTI classification model"""
        print("🧠 Training MBTI model...")
        
        # Create demo dataset
        mbti_df = self._create_demo_dataset()
        
        # Preprocess data
        mbti_df['processed_posts'] = mbti_df['posts'].apply(self._preprocess_text)
        mbti_df = mbti_df[mbti_df['processed_posts'].str.len() > 10]
        
        # Prepare features and labels
        X = mbti_df['processed_posts']
        y = mbti_df['type']
        
        # Vectorize text
        self.vectorizer = TfidfVectorizer(max_features=3000, stop_words='english', ngram_range=(1, 2))
        X_vec = self.vectorizer.fit_transform(X)
        
        # Train classifier
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        self.classifier.fit(X_vec, y)
        
        # Create compatibility matrix
        self.compatibility_matrix = self._create_compatibility_matrix()
        
        print("✅ MBTI model trained successfully!")
        print(f"📊 Training samples: {len(X)}")
        print(f"🎯 Features: {X_vec.shape[1]}")
    
    def predict_mbti(self, text):
        """Predict MBTI type from text"""
        processed_text = self._preprocess_text(text)
        
        if len(processed_text) < 5:
            return {
                'error': 'Text too short for analysis. Please provide more descriptive text.'
            }
        
        # Vectorize and predict
        text_vec = self.vectorizer.transform([processed_text])
        prediction = self.classifier.predict(text_vec)[0]
        probabilities = self.classifier.predict_proba(text_vec)[0]
        confidence = max(probabilities)
        
        # Get all probabilities for each type
        type_probabilities = dict(zip(self.classifier.classes_, probabilities))
        
        # Get compatibility scores
        compatibility_scores = self.compatibility_matrix.loc[prediction].sort_values(ascending=False)
        best_matches = compatibility_scores.head(5).to_dict()
        
        # Create dimensional breakdown
        dimensions = {
            'E_vs_I': 'Extroversion' if prediction[0] == 'E' else 'Introversion',
            'S_vs_N': 'Sensing' if prediction[1] == 'S' else 'Intuition',
            'T_vs_F': 'Thinking' if prediction[2] == 'T' else 'Feeling',
            'J_vs_P': 'Judging' if prediction[3] == 'J' else 'Perceiving'
        }
        
        return {
            'mbti_type': prediction,
            'confidence': float(confidence),
            'type_probabilities': {k: float(v) for k, v in type_probabilities.items()},
            'dimensional_breakdown': dimensions,
            'description': self._get_type_description(prediction),
            'best_compatibility_matches': best_matches,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _get_type_description(self, mbti_type):
        """Get description for MBTI type"""
        descriptions = {
            'INTJ': 'The Architect - Strategic and ambitious, with a plan for everything',
            'INTP': 'The Logician - Innovative inventors with an unquenchable thirst for knowledge',
            'ENTJ': 'The Commander - Bold, imaginative and strong-willed leaders',
            'ENTP': 'The Debater - Smart and curious thinkers who cannot resist an intellectual challenge',
            'INFJ': 'The Advocate - Creative and insightful, inspired and independent',
            'INFP': 'The Mediator - Poetic, kind and altruistic people, always eager to help',
            'ENFJ': 'The Protagonist - Charismatic and inspiring leaders, able to mesmerize listeners',
            'ENFP': 'The Campaigner - Enthusiastic, creative and sociable free spirits',
            'ISTJ': 'The Logistician - Practical and fact-minded, reliable and responsible',
            'ISFJ': 'The Protector - Warm-hearted and dedicated, always ready to protect loved ones',
            'ESTJ': 'The Executive - Excellent administrators, unsurpassed at managing things or people',
            'ESFJ': 'The Consul - Extraordinarily caring, social and popular people, always eager to help',
            'ISTP': 'The Virtuoso - Bold and practical experimenters, masters of all kinds of tools',
            'ISFP': 'The Adventurer - Flexible and charming artists, always ready to explore new possibilities',
            'ESTP': 'The Entrepreneur - Smart, energetic and perceptive people, truly enjoy living on the edge',
            'ESFP': 'The Entertainer - Spontaneous, energetic and enthusiastic people - life is never boring'
        }
        return descriptions.get(mbti_type, 'Unknown MBTI type')

# Initialize the analyzer
mbti_analyzer = MBTIAnalyzer()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'MBTI Analysis Service',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/predict', methods=['POST'])
def predict_mbti():
    """Main prediction endpoint"""
    try:
        # Get JSON data
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if 'text' not in data:
            return jsonify({'error': 'Missing "text" field in JSON data'}), 400
        
        text = data['text']
        
        if not text or not text.strip():
            return jsonify({'error': 'Text field is empty'}), 400
        
        # Analyze the text
        result = mbti_analyzer.predict_mbti(text)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/types', methods=['GET'])
def get_mbti_types():
    """Get all MBTI types with descriptions"""
    types_info = {}
    for mbti_type in mbti_analyzer.mbti_types:
        types_info[mbti_type] = mbti_analyzer._get_type_description(mbti_type)
    
    return jsonify({
        'mbti_types': types_info,
        'total_types': len(mbti_analyzer.mbti_types)
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information"""
    return jsonify({
        'service': 'MBTI Analysis Service',
        'version': '1.0.0',
        'endpoints': {
            'POST /predict': 'Analyze text and predict MBTI type',
            'GET /types': 'Get all MBTI types and descriptions',
            'GET /health': 'Health check'
        },
        'usage': {
            'method': 'POST',
            'url': '/predict',
            'content_type': 'application/json',
            'body': {'text': 'Your text to analyze here...'}
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8070))
    app.run(host='0.0.0.0', port=port, debug=False) 