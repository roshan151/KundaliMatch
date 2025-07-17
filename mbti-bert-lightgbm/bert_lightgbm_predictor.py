#!/usr/bin/env python3
"""
BERT + LightGBM MBTI Predictor

This script loads trained BERT + LightGBM models and provides 
prediction capabilities for new text inputs.
"""

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import joblib

# BERT and Transformers
from sentence_transformers import SentenceTransformer
import lightgbm as lgb

class BERTLightGBMMBTIPredictor:
    """
    MBTI Predictor using pre-trained BERT + LightGBM models
    """
    
    def __init__(self, model_metadata_path: str):
        """
        Initialize predictor with trained models
        
        Args:
            model_metadata_path: Path to model metadata JSON file
        """
        self.metadata_path = Path(model_metadata_path)
        self.models_dir = self.metadata_path.parent
        
        # Load metadata
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        self.mbti_types = self.metadata['mbti_types']
        
        # Load models
        self._load_models()
        
        print(f"✅ MBTI Predictor initialized successfully!")
        
        # Handle both old and new metadata formats
        accuracy_key = 'holdout_accuracy' if 'holdout_accuracy' in self.metadata else 'test_accuracy'
        print(f"📊 Model accuracy: {self.metadata[accuracy_key]:.4f}")
        print(f"🤖 BERT model: {self.metadata['bert_model']}")
        
        if 'data_split' in self.metadata:
            print(f"📊 Data split: {self.metadata['data_split']}")
        if 'overfitting_prevention' in self.metadata:
            print(f"🛡️ Overfitting prevention enabled")
    
    def _load_models(self):
        """Load all trained models"""
        model_files = self.metadata['model_files']
        
        # Load BERT model
        bert_config_path = Path(model_files['bert_config'])
        with open(bert_config_path, 'r') as f:
            bert_config = json.load(f)
        
        print(f"🤖 Loading BERT model: {bert_config['model_name']}")
        self.bert_model = SentenceTransformer(bert_config['model_name'])
        
        # Load LightGBM model
        lgb_model_path = Path(model_files['lightgbm_model'])
        print(f"🌟 Loading LightGBM model from: {lgb_model_path}")
        self.lgb_model = joblib.load(lgb_model_path)
        
        # Load label encoder
        encoder_path = Path(model_files['label_encoder'])
        print(f"🏷️ Loading label encoder from: {encoder_path}")
        self.label_encoder = joblib.load(encoder_path)
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for prediction
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned text
        """
        # Remove URLs, mentions, and special characters
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'[^a-zA-Z\s.,!?]', '', text)
        
        # Clean extra whitespace
        text = ' '.join(text.split())
        text = text.strip()
        
        return text
    
    def predict_mbti(self, text: str, return_probabilities: bool = False) -> Dict:
        """
        Predict MBTI type from text
        
        Args:
            text: Input text
            return_probabilities: Whether to return prediction probabilities
            
        Returns:
            Dictionary with prediction results
        """
        # Preprocess text
        processed_text = self.preprocess_text(text)
        
        if len(processed_text.strip()) < 10:
            return {
                'error': 'Text too short for reliable prediction',
                'min_length': 10
            }
        
        # Generate BERT embedding
        embedding = self.bert_model.encode([processed_text], convert_to_numpy=True)
        
        # Make prediction
        prediction_encoded = self.lgb_model.predict(embedding)[0]
        prediction_proba = self.lgb_model.predict_proba(embedding)[0]
        
        # Decode prediction
        predicted_mbti = self.label_encoder.inverse_transform([prediction_encoded])[0]
        confidence = np.max(prediction_proba)
        
        result = {
            'mbti_type': predicted_mbti,
            'confidence': float(confidence),
            'processed_text': processed_text
        }
        
        if return_probabilities:
            # Get probabilities for all types
            type_probabilities = {}
            for i, mbti_type in enumerate(self.mbti_types):
                encoded_label = self.label_encoder.transform([mbti_type])[0]
                type_probabilities[mbti_type] = float(prediction_proba[encoded_label])
            
            # Sort by probability
            sorted_probabilities = dict(
                sorted(type_probabilities.items(), key=lambda x: x[1], reverse=True)
            )
            
            result['all_probabilities'] = sorted_probabilities
            result['top_3_predictions'] = list(sorted_probabilities.keys())[:3]
        
        return result
    
    def predict_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict]:
        """
        Predict MBTI types for multiple texts
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            
        Returns:
            List of prediction dictionaries
        """
        print(f"🔄 Processing {len(texts)} texts in batches of {batch_size}")
        
        results = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            
            # Preprocess batch
            processed_texts = [self.preprocess_text(text) for text in batch_texts]
            
            # Generate embeddings for batch
            embeddings = self.bert_model.encode(processed_texts, convert_to_numpy=True)
            
            # Make predictions for batch
            predictions_encoded = self.lgb_model.predict(embeddings)
            predictions_proba = self.lgb_model.predict_proba(embeddings)
            
            # Process batch results
            for j, (original_text, processed_text) in enumerate(zip(batch_texts, processed_texts)):
                if len(processed_text.strip()) < 10:
                    results.append({
                        'error': 'Text too short for reliable prediction',
                        'original_text': original_text,
                        'min_length': 10
                    })
                    continue
                
                predicted_mbti = self.label_encoder.inverse_transform([predictions_encoded[j]])[0]
                confidence = np.max(predictions_proba[j])
                
                results.append({
                    'mbti_type': predicted_mbti,
                    'confidence': float(confidence),
                    'original_text': original_text,
                    'processed_text': processed_text
                })
        
        return results
    
    def analyze_personality_traits(self, text: str) -> Dict:
        """
        Analyze personality traits from text
        
        Args:
            text: Input text
            
        Returns:
            Detailed personality analysis
        """
        prediction = self.predict_mbti(text, return_probabilities=True)
        
        if 'error' in prediction:
            return prediction
        
        mbti_type = prediction['mbti_type']
        
        # Extract individual dimensions
        dimensions = {
            'Energy': 'Extroversion (E)' if mbti_type[0] == 'E' else 'Introversion (I)',
            'Information': 'Intuition (N)' if mbti_type[1] == 'N' else 'Sensing (S)',
            'Decisions': 'Thinking (T)' if mbti_type[2] == 'T' else 'Feeling (F)',
            'Lifestyle': 'Judging (J)' if mbti_type[3] == 'J' else 'Perceiving (P)'
        }
        
        # Add personality descriptions
        personality_descriptions = {
            'INTJ': 'The Architect - Strategic, independent, and visionary',
            'INTP': 'The Thinker - Analytical, innovative, and logical',
            'ENTJ': 'The Commander - Natural leader, decisive, and strategic',
            'ENTP': 'The Debater - Quick-witted, clever, and adaptable',
            'INFJ': 'The Advocate - Insightful, principled, and creative',
            'INFP': 'The Mediator - Idealistic, adaptable, and caring',
            'ENFJ': 'The Protagonist - Charismatic, inspiring, and altruistic',
            'ENFP': 'The Campaigner - Enthusiastic, creative, and spontaneous',
            'ISTJ': 'The Logistician - Practical, fact-minded, and reliable',
            'ISFJ': 'The Protector - Warm-hearted, conscientious, and harmonious',
            'ESTJ': 'The Executive - Organized, practical, and decisive',
            'ESFJ': 'The Consul - Caring, social, and popular',
            'ISTP': 'The Virtuoso - Bold, practical, and experimental',
            'ISFP': 'The Adventurer - Charming, sensitive, and artistic',
            'ESTP': 'The Entrepreneur - Smart, energetic, and perceptive',
            'ESFP': 'The Entertainer - Spontaneous, enthusiastic, and playful'
        }
        
        return {
            'mbti_type': mbti_type,
            'confidence': prediction['confidence'],
            'description': personality_descriptions.get(mbti_type, 'Unknown type'),
            'dimensions': dimensions,
            'top_3_predictions': prediction.get('top_3_predictions', []),
            'all_probabilities': prediction.get('all_probabilities', {}),
            'analysis_quality': 'High' if prediction['confidence'] > 0.7 else 'Medium' if prediction['confidence'] > 0.5 else 'Low'
        }


def load_latest_model() -> Optional[str]:
    """
    Find and return path to latest trained model metadata
    
    Returns:
        Path to latest model metadata file or None if not found
    """
    models_dir = Path('./models')
    if not models_dir.exists():
        return None
    
    # Find all metadata files
    metadata_files = list(models_dir.glob('model_metadata_*.json'))
    
    if not metadata_files:
        return None
    
    # Return the latest one (by filename timestamp)
    latest_metadata = sorted(metadata_files)[-1]
    return str(latest_metadata)


def demo_predictions():
    """Demo function showing various prediction examples"""
    
    # Load latest model
    latest_model_path = load_latest_model()
    if not latest_model_path:
        print("❌ No trained models found. Please run training first.")
        return
    
    print(f"🔍 Loading model from: {latest_model_path}")
    predictor = BERTLightGBMMBTIPredictor(latest_model_path)
    
    # Demo texts
    demo_texts = [
        "I love planning everything in advance and organizing my schedule. I prefer logical decision-making and clear structures in my work.",
        
        "I enjoy meeting new people and exploring creative possibilities. I go with the flow and adapt easily to new situations.",
        
        "I prefer quiet environments and deep conversations. I value harmony and understanding others' feelings when making decisions.",
        
        "I'm very practical and focus on details. I like step-by-step processes and prefer facts over theories.",
        
        "I'm always thinking about future possibilities and love discussing abstract concepts and innovative ideas."
    ]
    
    print("\n🧪 Demo Predictions:")
    print("=" * 70)
    
    for i, text in enumerate(demo_texts, 1):
        print(f"\n📝 Text {i}: {text[:60]}...")
        
        # Get detailed analysis
        analysis = predictor.analyze_personality_traits(text)
        
        if 'error' in analysis:
            print(f"   ❌ Error: {analysis['error']}")
            continue
        
        print(f"   🎯 Predicted MBTI: {analysis['mbti_type']} ({analysis['confidence']:.3f} confidence)")
        print(f"   📖 Description: {analysis['description']}")
        print(f"   🏆 Top 3 types: {', '.join(analysis['top_3_predictions'])}")
        print(f"   ⭐ Analysis quality: {analysis['analysis_quality']}")
    
    # Batch prediction demo
    print(f"\n🚀 Batch Prediction Demo:")
    batch_results = predictor.predict_batch(demo_texts)
    
    batch_summary = {}
    for result in batch_results:
        if 'mbti_type' in result:
            mbti_type = result['mbti_type']
            batch_summary[mbti_type] = batch_summary.get(mbti_type, 0) + 1
    
    print(f"   📊 Predicted types distribution: {batch_summary}")


if __name__ == "__main__":
    demo_predictions() 