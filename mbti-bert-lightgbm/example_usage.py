#!/usr/bin/env python3
"""
Example Usage of BERT + LightGBM MBTI Classifier

This script demonstrates:
1. Training a new model
2. Loading and using trained models
3. Making predictions on new text
4. Batch processing
"""

from bert_lightgbm_trainer import BERTLightGBMMBTITrainer
from bert_lightgbm_predictor import BERTLightGBMMBTIPredictor, load_latest_model
import json

def train_new_model():
    """Train a new BERT + LightGBM model"""
    print("🏋️ Training New BERT + LightGBM Model")
    print("=" * 50)
    
    # Initialize trainer
    trainer = BERTLightGBMMBTITrainer(
        bert_model_name='all-MiniLM-L6-v2',  # Fast and efficient
        random_state=42
    )
    
    # Train the model
    results = trainer.train_complete_pipeline()
    
    print(f"\n✅ Training completed!")
    print(f"   Test Accuracy: {results['evaluation_results']['accuracy']:.4f}")
    print(f"   CV Accuracy: {results['cv_results']['mean_accuracy']:.4f}")
    print(f"   Model saved to: {results['metadata_path']}")
    
    return results['metadata_path']

def use_trained_model(metadata_path: str = None):
    """Use a trained model for predictions"""
    print("\n🔮 Using Trained Model for Predictions")
    print("=" * 50)
    
    # Load model (latest if no path specified)
    if metadata_path is None:
        metadata_path = load_latest_model()
        if metadata_path is None:
            print("❌ No trained model found. Please train a model first.")
            return
    
    # Initialize predictor
    predictor = BERTLightGBMMBTIPredictor(metadata_path)
    
    # Example texts for prediction
    sample_texts = [
        {
            'text': "I love planning everything in advance and organizing my schedule. I prefer logical decision-making and clear structures in my work. I'm very goal-oriented and like to have everything under control.",
            'expected': 'ESTJ or similar J-type'
        },
        {
            'text': "I enjoy meeting new people and exploring creative possibilities. I go with the flow and adapt easily to new situations. I love brainstorming and coming up with innovative ideas.",
            'expected': 'ENFP or similar N-type'
        },
        {
            'text': "I prefer quiet environments and deep conversations. I value harmony and understanding others' feelings when making decisions. I'm very empathetic and care about personal relationships.",
            'expected': 'INFP or similar F-type'
        },
        {
            'text': "I'm very practical and focus on details. I like step-by-step processes and prefer facts over theories. I'm reliable and like to follow established procedures.",
            'expected': 'ISTJ or similar S-type'
        },
        {
            'text': "I'm always thinking about future possibilities and love discussing abstract concepts and innovative ideas. I enjoy theoretical discussions and exploring new concepts.",
            'expected': 'INTP or similar N-type'
        }
    ]
    
    print("\n📝 Single Predictions:")
    for i, sample in enumerate(sample_texts, 1):
        print(f"\n--- Sample {i} ---")
        print(f"Text: {sample['text'][:100]}...")
        print(f"Expected: {sample['expected']}")
        
        # Get detailed analysis
        analysis = predictor.analyze_personality_traits(sample['text'])
        
        if 'error' in analysis:
            print(f"❌ Error: {analysis['error']}")
            continue
        
        print(f"🎯 Predicted: {analysis['mbti_type']} ({analysis['confidence']:.3f} confidence)")
        print(f"📖 Description: {analysis['description']}")
        print(f"🏆 Top 3: {', '.join(analysis['top_3_predictions'])}")
        print(f"⭐ Quality: {analysis['analysis_quality']}")
        
        # Show personality dimensions
        print("📊 Dimensions:")
        for dimension, trait in analysis['dimensions'].items():
            print(f"   {dimension}: {trait}")
    
    # Batch prediction example
    print(f"\n🚀 Batch Prediction Example:")
    all_texts = [sample['text'] for sample in sample_texts]
    batch_results = predictor.predict_batch(all_texts)
    
    print("Batch Results Summary:")
    type_counts = {}
    for result in batch_results:
        if 'mbti_type' in result:
            mbti_type = result['mbti_type']
            type_counts[mbti_type] = type_counts.get(mbti_type, 0) + 1
    
    print(f"   Type distribution: {type_counts}")
    
    # Show individual batch results
    print("\nIndividual Batch Results:")
    for i, result in enumerate(batch_results, 1):
        if 'mbti_type' in result:
            print(f"   {i}. {result['mbti_type']} (confidence: {result['confidence']:.3f})")
        else:
            print(f"   {i}. Error: {result.get('error', 'Unknown error')}")

def compare_with_expectations():
    """Compare predictions with expected personality types"""
    print("\n📊 Comparison with Expected Types")
    print("=" * 50)
    
    # Load latest model
    metadata_path = load_latest_model()
    if metadata_path is None:
        print("❌ No trained model found.")
        return
    
    predictor = BERTLightGBMMBTIPredictor(metadata_path)
    
    # Test cases with known personality indicators
    test_cases = [
        {
            'text': "I am extremely organized and always plan ahead. I make decisions based on logic and efficiency. I prefer structure and clear expectations in my work environment.",
            'expected_dimension': 'J (Judging), T (Thinking)',
            'expected_types': ['ESTJ', 'ENTJ', 'ISTJ', 'INTJ']
        },
        {
            'text': "I love spontaneous adventures and meeting new people. I'm very social and energetic. I prefer to keep my options open and adapt to situations as they come.",
            'expected_dimension': 'E (Extroversion), P (Perceiving)',
            'expected_types': ['ESFP', 'ENFP', 'ESTP', 'ENTP']
        },
        {
            'text': "I enjoy deep, meaningful conversations and prefer small groups over large parties. I focus on how decisions affect people and value harmony in relationships.",
            'expected_dimension': 'I (Introversion), F (Feeling)',
            'expected_types': ['INFP', 'ISFP', 'INFJ', 'ISFJ']
        }
    ]
    
    correct_predictions = 0
    total_predictions = len(test_cases)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Text: {case['text'][:80]}...")
        print(f"Expected dimension: {case['expected_dimension']}")
        print(f"Expected types: {', '.join(case['expected_types'])}")
        
        result = predictor.predict_mbti(case['text'], return_probabilities=True)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            continue
        
        predicted_type = result['mbti_type']
        is_correct = predicted_type in case['expected_types']
        
        print(f"🎯 Predicted: {predicted_type} ({'✅ Correct' if is_correct else '❌ Incorrect'})")
        print(f"📈 Confidence: {result['confidence']:.3f}")
        print(f"🏆 Top 3: {', '.join(result['top_3_predictions'])}")
        
        if is_correct:
            correct_predictions += 1
        
        # Check if any of top 3 predictions are correct
        top_3_correct = any(pred in case['expected_types'] for pred in result['top_3_predictions'])
        print(f"📊 Top-3 contains correct: {'✅ Yes' if top_3_correct else '❌ No'}")
    
    accuracy = correct_predictions / total_predictions
    print(f"\n📈 Overall Test Accuracy: {accuracy:.2%} ({correct_predictions}/{total_predictions})")

def main():
    """Main example function"""
    print("🧠 BERT + LightGBM MBTI Classifier - Example Usage")
    print("=" * 60)
    
    # Check if we have a trained model
    existing_model = load_latest_model()
    
    if existing_model:
        print(f"✅ Found existing model: {existing_model}")
        print("Would you like to:")
        print("1. Use existing model")
        print("2. Train new model")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            print("\n🏋️ Training new model...")
            metadata_path = train_new_model()
        else:
            metadata_path = existing_model
    else:
        print("📦 No existing model found. Training new model...")
        metadata_path = train_new_model()
    
    # Use the model for predictions
    use_trained_model(metadata_path)
    
    # Compare with expectations
    compare_with_expectations()
    
    print("\n🎉 Example completed successfully!")
    print("💡 You can now use the trained model for your own predictions.")

if __name__ == "__main__":
    main() 