#!/usr/bin/env python3
"""
BERT + LightGBM MBTI Classifier Training

This script trains an MBTI personality classifier using:
- BERT embeddings for text representation
- LightGBM for classification
- Advanced preprocessing and evaluation
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import re
import warnings
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import pickle
import joblib

# Machine Learning
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb

# BERT and Transformers
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8')

class BERTLightGBMMBTITrainer:
    """
    MBTI Classifier using BERT embeddings and LightGBM
    """
    
    def __init__(self, 
                 bert_model_name: str = 'all-MiniLM-L6-v2',
                 random_state: int = 42):
        """
        Initialize the trainer
        
        Args:
            bert_model_name: Name of the sentence-transformers model
            random_state: Random state for reproducibility
        """
        self.bert_model_name = bert_model_name
        self.random_state = random_state
        self.bert_model = None
        self.lgb_model = None
        self.label_encoder = LabelEncoder()
        self.mbti_types = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP',
                          'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']
        
        # Set up directories
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories"""
        self.base_dir = Path('.')
        self.data_dir = Path('../aligned-recommender/data/kaggle_mbti')
        self.outputs_dir = Path('./outputs')
        self.models_dir = Path('./models')
        
        # Create directories
        for directory in [self.outputs_dir, self.models_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for BERT embedding
        
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
    
    def load_dataset(self) -> pd.DataFrame:
        """
        Load MBTI dataset
        
        Returns:
            DataFrame with MBTI data
        """
        try:
            # Try to load real MBTI dataset
            mbti_df = pd.read_csv(self.data_dir / 'mbti_1.csv')
            print(f"✅ Loaded real MBTI dataset with {len(mbti_df)} users")
            self.real_data = True
        except FileNotFoundError:
            print("⚠️ Real MBTI dataset not found. Creating demo dataset...")
            # Create demo MBTI dataset
            demo_data = []
            for i in range(2000):  # Create 2000 demo users for better training
                mbti_type = np.random.choice(self.mbti_types)
                
                # Generate personality-appropriate text
                posts = []
                if 'I' in mbti_type:
                    posts.append("I prefer quiet environments and deep conversations. I enjoy reading and thinking.")
                    posts.append("I need time alone to recharge. Small groups are better than large parties.")
                else:
                    posts.append("I love meeting new people and being social. I enjoy parties and group activities.")
                    posts.append("I get energized by being around others. I love networking events.")
                
                if 'N' in mbti_type:
                    posts.append("I'm interested in possibilities and future potential. I like abstract concepts.")
                    posts.append("I enjoy discussing theories and ideas. Innovation excites me.")
                else:
                    posts.append("I focus on practical details and current realities. I prefer concrete information.")
                    posts.append("I like step-by-step processes. Facts and data are important to me.")
                
                if 'T' in mbti_type:
                    posts.append("I make decisions based on logic and analysis. Objectivity is important.")
                    posts.append("I value efficiency and competence. I can be direct in my communication.")
                else:
                    posts.append("I consider feelings and values when making decisions. Harmony matters to me.")
                    posts.append("I'm empathetic and like to help others. I consider personal impact.")
                
                if 'J' in mbti_type:
                    posts.append("I like structure and planning ahead. Deadlines help me organize my work.")
                    posts.append("I prefer closure and decided matters. I like to have things settled.")
                else:
                    posts.append("I prefer flexibility and spontaneity. I adapt well to changes.")
                    posts.append("I like to keep options open. I work well under pressure at the last minute.")
                
                # Combine posts
                combined_posts = " ".join(posts)
                demo_data.append({'type': mbti_type, 'posts': combined_posts})
            
            mbti_df = pd.DataFrame(demo_data)
            self.real_data = False
        
        print(f"📊 MBTI Dataset loaded: {len(mbti_df)} users")
        print(f"📋 Columns: {list(mbti_df.columns)}")
        print(f"🏷️ MBTI Types: {mbti_df['type'].nunique()} unique types")
        
        return mbti_df
    
    def analyze_dataset(self, df: pd.DataFrame):
        """
        Analyze and visualize the dataset
        
        Args:
            df: MBTI DataFrame
        """
        # Type distribution
        type_counts = df['type'].value_counts()
        print("\n📊 MBTI Type Distribution:")
        for mbti_type, count in type_counts.items():
            percentage = (count / len(df)) * 100
            print(f"   {mbti_type}: {count} users ({percentage:.1f}%)")
        
        # Visualize distribution
        plt.figure(figsize=(15, 6))
        sns.countplot(data=df, x='type', order=self.mbti_types, palette='viridis')
        plt.title('MBTI Type Distribution', fontsize=16)
        plt.xlabel('MBTI Type')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.outputs_dir / 'mbti_distribution.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # Text length analysis
        df['text_length'] = df['posts'].str.len()
        print(f"\n📝 Text Statistics:")
        print(f"   Average text length: {df['text_length'].mean():.0f} characters")
        print(f"   Median text length: {df['text_length'].median():.0f} characters")
        print(f"   Min text length: {df['text_length'].min():.0f} characters")
        print(f"   Max text length: {df['text_length'].max():.0f} characters")
    
    def load_bert_model(self):
        """Load BERT model for embeddings"""
        print(f"\n🤖 Loading BERT model: {self.bert_model_name}")
        self.bert_model = SentenceTransformer(self.bert_model_name)
        print(f"✅ BERT model loaded successfully")
        print(f"📏 Embedding dimension: {self.bert_model.get_sentence_embedding_dimension()}")
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate BERT embeddings for texts
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            Numpy array of embeddings
        """
        print(f"\n🔄 Generating BERT embeddings for {len(texts)} texts...")
        
        # Process in batches with progress bar
        embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = self.bert_model.encode(batch_texts, 
                                                    convert_to_numpy=True,
                                                    show_progress_bar=False)
            embeddings.append(batch_embeddings)
        
        embeddings = np.vstack(embeddings)
        print(f"✅ Embeddings generated. Shape: {embeddings.shape}")
        
        return embeddings
    
    def train_lightgbm(self, X_train: np.ndarray, y_train: np.ndarray, 
                      X_test: np.ndarray, y_test: np.ndarray) -> lgb.LGBMClassifier:
        """
        Train LightGBM classifier with overfitting prevention
        
        Args:
            X_train: Training features (70%)
            y_train: Training labels (70%)
            X_test: Test features for early stopping (15%)
            y_test: Test labels for early stopping (15%)
            
        Returns:
            Trained LightGBM model
        """
        print("\n🌟 Training LightGBM classifier with overfitting prevention...")
        
        # Enhanced LightGBM parameters for overfitting prevention
        lgb_params = {
            'objective': 'multiclass',
            'num_class': len(self.mbti_types),
            'boosting_type': 'gbdt',
            
            # Reduced model complexity to prevent overfitting
            'num_leaves': 20,  # Reduced from 31
            'max_depth': 6,    # Limit tree depth
            'learning_rate': 0.02,  # Lower learning rate
            
            # Regularization parameters
            'reg_alpha': 0.1,  # L1 regularization
            'reg_lambda': 0.1,  # L2 regularization
            'min_child_samples': 50,  # Minimum samples in leaf
            'min_child_weight': 0.001,
            
            # Feature and data subsampling for generalization
            'feature_fraction': 0.8,  # Use 80% of features per tree
            'bagging_fraction': 0.7,  # Use 70% of data per iteration
            'bagging_freq': 5,
            
            # Training settings
            'verbose': 0,
            'random_state': self.random_state,
            'n_estimators': 2000,  # More trees but with early stopping
            'early_stopping_rounds': 150,  # More patience for early stopping
            'eval_metric': 'multi_logloss',
            
            # Additional overfitting prevention
            'subsample_for_bin': 200000,
            'min_split_gain': 0.0,
        }
        
        # Create and train model
        model = lgb.LGBMClassifier(**lgb_params)
        
        print(f"📊 Training with regularization:")
        print(f"   Learning rate: {lgb_params['learning_rate']}")
        print(f"   Max depth: {lgb_params['max_depth']}")
        print(f"   L1/L2 regularization: {lgb_params['reg_alpha']}/{lgb_params['reg_lambda']}")
        print(f"   Feature fraction: {lgb_params['feature_fraction']}")
        print(f"   Bagging fraction: {lgb_params['bagging_fraction']}")
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            eval_names=['train', 'test'],
            callbacks=[lgb.log_evaluation(period=200), lgb.early_stopping(150)]
        )
        
        print(f"✅ LightGBM training completed")
        print(f"📊 Best iteration: {model.best_iteration_}")
        print(f"📈 Train score: {model.best_score_['train']['multi_logloss']:.4f}")
        print(f"📈 Test score: {model.best_score_['test']['multi_logloss']:.4f}")
        
        # Check for overfitting
        train_score = model.best_score_['train']['multi_logloss']
        test_score = model.best_score_['test']['multi_logloss']
        overfitting_ratio = (test_score - train_score) / train_score
        
        print(f"🔍 Overfitting check:")
        print(f"   Score difference: {test_score - train_score:.4f}")
        print(f"   Overfitting ratio: {overfitting_ratio:.2%}")
        
        if overfitting_ratio > 0.1:  # More than 10% worse on test
            print("⚠️  Warning: Potential overfitting detected!")
        else:
            print("✅ Good generalization - no significant overfitting")
        
        return model
    
    def evaluate_model(self, model: lgb.LGBMClassifier, 
                      X_holdout: np.ndarray, y_holdout: np.ndarray) -> Dict:
        """
        Evaluate the trained model on holdout set (final evaluation)
        
        Args:
            model: Trained LightGBM model
            X_holdout: Holdout features (15% - completely unseen during training)
            y_holdout: Holdout labels (15% - completely unseen during training)
            
        Returns:
            Evaluation metrics
        """
        print("\n📊 Final model evaluation on holdout set...")
        print("🔒 This is the first time the model sees this data!")
        
        # Predictions
        y_pred = model.predict(X_holdout)
        y_pred_proba = model.predict_proba(X_holdout)
        
        # Calculate metrics
        accuracy = accuracy_score(y_holdout, y_pred)
        
        print(f"🎯 Holdout Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
        
        # Classification report
        print("\n📋 Detailed Classification Report (Holdout Set):")
        report = classification_report(y_holdout, y_pred, 
                                     target_names=self.mbti_types,
                                     output_dict=True)
        print(classification_report(y_holdout, y_pred, target_names=self.mbti_types))
        
        # Confusion matrix
        cm = confusion_matrix(y_holdout, y_pred)
        
        # Plot confusion matrix
        plt.figure(figsize=(12, 10))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=self.mbti_types, yticklabels=self.mbti_types)
        plt.title('Confusion Matrix - BERT + LightGBM (Holdout Set)')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.tight_layout()
        plt.savefig(self.outputs_dir / 'confusion_matrix_holdout.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # Feature importance (top 20)
        if hasattr(model, 'feature_importances_'):
            feature_importance = model.feature_importances_
            top_indices = np.argsort(feature_importance)[-20:]
            
            plt.figure(figsize=(10, 8))
            plt.barh(range(20), feature_importance[top_indices])
            plt.title('Top 20 Feature Importances (BERT Embedding Dimensions)')
            plt.xlabel('Importance')
            plt.ylabel('Feature Index')
            plt.tight_layout()
            plt.savefig(self.outputs_dir / 'feature_importance.png', dpi=300, bbox_inches='tight')
            plt.show()
        
        return {
            'accuracy': accuracy,
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'predictions': y_pred.tolist(),
            'probabilities': y_pred_proba.tolist()
        }
    
    def cross_validate(self, X: np.ndarray, y: np.ndarray, cv_folds: int = 5) -> Dict:
        """
        Perform cross-validation
        
        Args:
            X: Features
            y: Labels
            cv_folds: Number of CV folds
            
        Returns:
            Cross-validation results
        """
        print(f"\n🔄 Performing {cv_folds}-fold cross-validation...")
        
        # Create model for CV
        lgb_model = lgb.LGBMClassifier(
            objective='multiclass',
            num_class=len(self.mbti_types),
            n_estimators=500,
            random_state=self.random_state,
            verbose=-1
        )
        
        # Stratified K-Fold
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        
        # Cross-validation scores
        cv_scores = cross_val_score(lgb_model, X, y, cv=skf, scoring='accuracy', n_jobs=-1)
        
        print(f"📊 Cross-validation results:")
        print(f"   Mean Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        print(f"   Individual scores: {cv_scores}")
        
        return {
            'cv_scores': cv_scores.tolist(),
            'mean_accuracy': cv_scores.mean(),
            'std_accuracy': cv_scores.std()
        }
    
    def save_models(self, model: lgb.LGBMClassifier, embeddings: np.ndarray, 
                   evaluation_results: Dict, cv_results: Dict):
        """
        Save trained models and results
        
        Args:
            model: Trained LightGBM model
            embeddings: BERT embeddings
            evaluation_results: Model evaluation metrics
            cv_results: Cross-validation results
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print(f"\n💾 Saving models and results...")
        
        # Save LightGBM model
        model_path = self.models_dir / f'bert_lightgbm_model_{timestamp}.pkl'
        joblib.dump(model, model_path)
        
        # Save BERT model name (for loading later)
        bert_config = {
            'model_name': self.bert_model_name,
            'embedding_dim': self.bert_model.get_sentence_embedding_dimension()
        }
        bert_config_path = self.models_dir / f'bert_config_{timestamp}.json'
        with open(bert_config_path, 'w') as f:
            json.dump(bert_config, f, indent=2)
        
        # Save label encoder
        encoder_path = self.models_dir / f'label_encoder_{timestamp}.pkl'
        joblib.dump(self.label_encoder, encoder_path)
        
        # Save embeddings (optional - for analysis)
        embeddings_path = self.models_dir / f'bert_embeddings_{timestamp}.npy'
        np.save(embeddings_path, embeddings)
        
        # Save comprehensive metadata
        metadata = {
            'model_type': 'BERT + LightGBM (Overfitting Prevention)',
            'bert_model': self.bert_model_name,
            'embedding_dimension': bert_config['embedding_dim'],
            'holdout_accuracy': evaluation_results['accuracy'],
            'cv_mean_accuracy': cv_results['mean_accuracy'],
            'cv_std_accuracy': cv_results['std_accuracy'],
            'data_split': '70% train, 15% test (early stopping), 15% holdout (final eval)',
            'overfitting_prevention': {
                'regularization': 'L1 + L2',
                'feature_fraction': 0.8,
                'bagging_fraction': 0.7,
                'early_stopping': 150,
                'reduced_complexity': 'max_depth=6, num_leaves=20'
            },
            'mbti_types': self.mbti_types,
            'training_timestamp': datetime.now().isoformat(),
            'data_source': 'real_kaggle' if self.real_data else 'demo_generated',
            'model_files': {
                'lightgbm_model': str(model_path),
                'bert_config': str(bert_config_path),
                'label_encoder': str(encoder_path),
                'embeddings': str(embeddings_path)
            }
        }
        
        metadata_path = self.models_dir / f'model_metadata_{timestamp}.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save evaluation results
        eval_path = self.outputs_dir / f'evaluation_results_{timestamp}.json'
        with open(eval_path, 'w') as f:
            json.dump(evaluation_results, f, indent=2)
        
        print(f"✅ Models and results saved:")
        print(f"   LightGBM Model: {model_path}")
        print(f"   BERT Config: {bert_config_path}")
        print(f"   Label Encoder: {encoder_path}")
        print(f"   Metadata: {metadata_path}")
        print(f"   Evaluation: {eval_path}")
        
        return metadata_path
    
    def train_complete_pipeline(self):
        """
        Run the complete training pipeline
        """
        print("🚀 Starting BERT + LightGBM MBTI Training Pipeline")
        print("=" * 60)
        
        # Load and analyze dataset
        df = self.load_dataset()
        self.analyze_dataset(df)
        
        # Preprocess text
        print("\n🔄 Preprocessing text data...")
        df['processed_posts'] = df['posts'].apply(self.preprocess_text)
        df = df[df['processed_posts'].str.len() > 20]  # Filter very short texts
        print(f"✅ After preprocessing: {len(df)} users with valid posts")
        
        # Load BERT model
        self.load_bert_model()
        
        # Prepare data
        X_text = df['processed_posts'].tolist()
        y = df['type'].values
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Generate BERT embeddings
        X_embeddings = self.generate_embeddings(X_text)
        
        # Three-way split: 70% train, 15% test (for early stopping), 15% holdout (for final evaluation)
        print(f"\n📊 Creating three-way data split (70-15-15)...")
        
        # First split: 70% train, 30% temp
        X_train, X_temp, y_train, y_temp = train_test_split(
            X_embeddings, y_encoded, test_size=0.3, random_state=self.random_state, 
            stratify=y_encoded
        )
        
        # Second split: Split 30% temp into 15% test and 15% holdout
        X_test, X_holdout, y_test, y_holdout = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=self.random_state,
            stratify=y_temp
        )
        
        print(f"\n📊 Data split distribution:")
        print(f"   🟢 Training: {len(X_train)} samples ({len(X_train)/len(X_embeddings)*100:.1f}%)")
        print(f"   🟡 Test (early stopping): {len(X_test)} samples ({len(X_test)/len(X_embeddings)*100:.1f}%)")
        print(f"   🔴 Holdout (final eval): {len(X_holdout)} samples ({len(X_holdout)/len(X_embeddings)*100:.1f}%)")
        
        print(f"\n🔒 Holdout set will remain completely unseen until final evaluation!")
        
        # Cross-validation on train+test combined (not including holdout)
        X_cv = np.vstack([X_train, X_test])
        y_cv = np.concatenate([y_train, y_test])
        print(f"\n🔄 Cross-validation on {len(X_cv)} samples (train + test, excluding holdout)...")
        cv_results = self.cross_validate(X_cv, y_cv)
        
        # Train model (using test set for early stopping, holdout completely hidden)
        model = self.train_lightgbm(X_train, y_train, X_test, y_test)
        
        # Final evaluation on completely unseen holdout set
        evaluation_results = self.evaluate_model(model, X_holdout, y_holdout)
        
        # Save everything
        metadata_path = self.save_models(model, X_embeddings, evaluation_results, cv_results)
        
        print("\n🎉 Training Pipeline Completed!")
        print("=" * 60)
        print(f"📈 Final Holdout Accuracy: {evaluation_results['accuracy']:.4f}")
        print(f"📊 CV Mean Accuracy: {cv_results['mean_accuracy']:.4f}")
        print(f"🔒 Holdout evaluation represents true unseen performance")
        print(f"💾 Metadata saved to: {metadata_path}")
        
        return {
            'model': model,
            'bert_model': self.bert_model,
            'label_encoder': self.label_encoder,
            'evaluation_results': evaluation_results,
            'cv_results': cv_results,
            'metadata_path': metadata_path
        }


def main():
    """Main training function"""
    # Initialize trainer
    trainer = BERTLightGBMMBTITrainer(
        bert_model_name='all-MiniLM-L6-v2',  # Efficient BERT model
        random_state=42
    )
    
    # Run training pipeline
    results = trainer.train_complete_pipeline()
    
    print("\n🏁 Training completed successfully!")
    return results


if __name__ == "__main__":
    results = main() 