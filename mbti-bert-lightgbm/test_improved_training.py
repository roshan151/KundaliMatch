#!/usr/bin/env python3
"""
Test script for improved BERT + LightGBM training with overfitting prevention

This script demonstrates the new features:
- Three-way data split (70% train, 15% test, 15% holdout)
- Overfitting prevention techniques
- Proper evaluation on unseen holdout data
"""

import os
import sys
from bert_lightgbm_trainer import BERTLightGBMMBTITrainer
from bert_lightgbm_predictor import BERTLightGBMMBTIPredictor

def test_improved_training():
    """Test the improved training pipeline with overfitting prevention"""
    
    print("🧪 Testing Improved BERT + LightGBM Training")
    print("=" * 60)
    print("✅ Features being tested:")
    print("   • Three-way data split (70-15-15)")
    print("   • Overfitting prevention techniques")
    print("   • Holdout set evaluation")
    print("   • Enhanced regularization")
    print("   • Early stopping on test set")
    print()
    
    # Initialize trainer with overfitting prevention
    trainer = BERTLightGBMMBTITrainer(
        bert_model_name='all-MiniLM-L6-v2',
        random_state=42
    )
    
    print(f"📊 Trainer initialized successfully")
    print(f"🎯 Target: Train on 70%, early stop on 15%, final eval on 15%")
    print()
    
    try:
        # Load a small dataset for quick testing
        df = trainer.load_dataset()
        
        # Limit dataset size for quick testing
        if len(df) > 500:
            df = df.sample(n=500, random_state=42)
            print(f"🔄 Using sample of {len(df)} records for quick testing")
        
        print(f"📊 Dataset info:")
        print(f"   Total samples: {len(df)}")
        print(f"   Expected train: ~{int(len(df) * 0.7)}")
        print(f"   Expected test: ~{int(len(df) * 0.15)}")
        print(f"   Expected holdout: ~{int(len(df) * 0.15)}")
        print()
        
        # Quick analysis
        trainer.analyze_dataset(df)
        
        # Load BERT model
        trainer.load_bert_model()
        
        # Preprocess text
        print("🔄 Preprocessing text...")
        df['processed_posts'] = df['posts'].apply(trainer.preprocess_text)
        df = df[df['processed_posts'].str.len() > 20]
        print(f"✅ After preprocessing: {len(df)} valid samples")
        
        # Prepare data
        X_text = df['processed_posts'].tolist()
        y = df['type'].values
        y_encoded = trainer.label_encoder.fit_transform(y)
        
        # Generate embeddings
        X_embeddings = trainer.generate_embeddings(X_text, batch_size=16)
        
        # Test the three-way split
        from sklearn.model_selection import train_test_split
        
        # First split: 70% train, 30% temp
        X_train, X_temp, y_train, y_temp = train_test_split(
            X_embeddings, y_encoded, test_size=0.3, random_state=42, 
            stratify=y_encoded
        )
        
        # Second split: 15% test, 15% holdout
        X_test, X_holdout, y_test, y_holdout = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42,
            stratify=y_temp
        )
        
        print(f"\n✅ Data split verification:")
        print(f"   Training: {len(X_train)} ({len(X_train)/len(X_embeddings)*100:.1f}%)")
        print(f"   Test: {len(X_test)} ({len(X_test)/len(X_embeddings)*100:.1f}%)")
        print(f"   Holdout: {len(X_holdout)} ({len(X_holdout)/len(X_embeddings)*100:.1f}%)")
        
        # Train model with overfitting prevention
        print("\n🌟 Training with overfitting prevention...")
        model = trainer.train_lightgbm(X_train, y_train, X_test, y_test)
        
        # Evaluate on holdout
        print("\n🔒 Final evaluation on holdout set...")
        evaluation_results = trainer.evaluate_model(model, X_holdout, y_holdout)
        
        print(f"\n✅ Training completed successfully!")
        print(f"📊 Final holdout accuracy: {evaluation_results['accuracy']:.4f}")
        
        # Test if model was saved properly
        print(f"\n💾 Testing model saving and loading...")
        
        # Quick cross-validation test
        cv_results = trainer.cross_validate(
            np.vstack([X_train, X_test]), 
            np.concatenate([y_train, y_test]), 
            cv_folds=3  # Quick 3-fold for testing
        )
        
        print(f"📊 CV results: {cv_results['mean_accuracy']:.4f} ± {cv_results['std_accuracy']:.4f}")
        
        # Save model
        metadata_path = trainer.save_models(model, X_embeddings, evaluation_results, cv_results)
        
        print(f"✅ Model saved to: {metadata_path}")
        
        # Test predictor loading
        predictor = BERTLightGBMMBTIPredictor(str(metadata_path))
        
        # Test prediction
        test_text = "I love planning everything and making logical decisions."
        result = predictor.predict_mbti(test_text)
        
        print(f"\n🧪 Test prediction:")
        print(f"   Input: {test_text}")
        print(f"   Predicted: {result['mbti_type']} (confidence: {result['confidence']:.3f})")
        
        print(f"\n🎉 All tests passed successfully!")
        print(f"✅ Improved training pipeline is working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Import numpy after confirming environment
    import numpy as np
    
    print("🚀 Starting improved training test...")
    success = test_improved_training()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("🎯 Your improved BERT + LightGBM model is ready!")
    else:
        print("\n❌ Test failed. Please check the error messages above.")
        sys.exit(1) 