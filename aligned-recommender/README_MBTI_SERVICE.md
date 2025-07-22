# 🧠 MBTI Analysis Service

A containerized REST API service that analyzes text input and predicts MBTI personality types using machine learning.

## Features

- **Text-to-MBTI Classification**: Analyzes text input and predicts one of 16 MBTI personality types
- **Confidence Scoring**: Provides confidence levels for predictions
- **Dimensional Breakdown**: Shows Extroversion/Introversion, Sensing/Intuition, Thinking/Feeling, Judging/Perceiving preferences
- **Compatibility Analysis**: Returns compatibility scores with other MBTI types
- **REST API**: Simple JSON-based HTTP API
- **Dockerized**: Ready-to-deploy container with health checks

## Quick Start

### Option 1: Using Docker

```bash
# Build the container
cd aligned-recommender
docker build -t mbti-service .

# Run the container
docker run -d -p 5000:5000 --name mbti-service mbti-service

# Test the service
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love meeting new people and solving complex problems collaboratively."}'
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements_service.txt

# Run the service
python mbti_service.py

# Service will be available at http://localhost:5000
```

## API Endpoints

### POST /predict
Analyze text and predict MBTI type.

**Request:**
```json
{
  "text": "Your text to analyze here..."
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "mbti_type": "ENFP",
    "confidence": 0.847,
    "type_probabilities": {
      "ENFP": 0.847,
      "ENFJ": 0.143,
      "ENTP": 0.089,
      "..."
    },
    "dimensional_breakdown": {
      "E_vs_I": "Extroversion",
      "S_vs_N": "Intuition",
      "T_vs_F": "Feeling",
      "J_vs_P": "Perceiving"
    },
    "description": "The Campaigner - Enthusiastic, creative and sociable free spirits",
    "best_compatibility_matches": {
      "INFJ": 94,
      "INTJ": 92,
      "ENFP": 81,
      "INFP": 78,
      "ENTP": 75
    },
    "analysis_timestamp": "2025-01-26T10:30:00.000000"
  }
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "MBTI Analysis Service",
  "version": "1.0.0",
  "timestamp": "2025-01-26T10:30:00.000000"
}
```

### GET /types
Get all MBTI types with descriptions.

**Response:**
```json
{
  "mbti_types": {
    "INTJ": "The Architect - Strategic and ambitious, with a plan for everything",
    "INTP": "The Logician - Innovative inventors with an unquenchable thirst for knowledge",
    "..."
  },
  "total_types": 16
}
```

### GET /
API information and usage guide.

## Testing

Use the provided test script to verify the service:

```bash
# Make the test script executable
chmod +x test_mbti_service.py

# Run comprehensive tests
python test_mbti_service.py

# Test with custom URL
python test_mbti_service.py http://your-service-url:5000
```

The test script will:
- Verify all endpoints are working
- Test various personality types
- Check error handling
- Run performance benchmarks

## Examples

### Introvert Thinker
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I prefer working alone and solving complex problems. I like to analyze data and make logical decisions based on facts."}'
```

Expected: INTJ, INTP, ISTJ, or ISTP

### Extrovert Feeler
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love meeting new people and making connections. I care deeply about others feelings and try to help everyone around me."}'
```

Expected: ENFJ, ENFP, ESFJ, or ESFP

## Docker Configuration

### Build Arguments
- Base image: `python:3.9-slim`
- Port: `5000`
- User: `mbtiuser` (non-root)

### Environment Variables
- `PORT`: Service port (default: 5000)

### Health Check
The container includes a health check that pings `/health` every 30 seconds.

## Model Details

- **Algorithm**: Random Forest Classifier with 100 estimators
- **Features**: TF-IDF vectorization with 3000 max features, unigrams and bigrams
- **Training Data**: Synthetic dataset with 2000 personality-appropriate text samples
- **Accuracy**: Varies based on text quality and length (typically 70-85%)
- **Response Time**: ~100-500ms per prediction

## Compatibility Matrix

The service includes a 16x16 compatibility matrix based on MBTI research:
- **Golden Pairs**: Highest compatibility (90-100%)
- **Same Type**: Good compatibility (75-85%)
- **Other Types**: Moderate to good compatibility (60-95%)

## Limitations

- **Demo Dataset**: Uses synthetic training data (not real personality assessments)
- **Text Length**: Requires meaningful text input (minimum ~5 characters after preprocessing)
- **Language**: Optimized for English text
- **Context**: Best results with personal/emotional content rather than technical text

## Production Deployment

For production use:

1. **Use Real Data**: Train with actual MBTI assessment data
2. **Scale**: Use gunicorn for production WSGI server
3. **Security**: Add authentication, rate limiting, and input validation
4. **Monitoring**: Add logging, metrics, and error tracking
5. **Performance**: Consider model optimization and caching

```bash
# Production Docker run with gunicorn
docker run -d -p 5000:5000 \
  -e WORKERS=4 \
  -e TIMEOUT=120 \
  --restart=unless-stopped \
  mbti-service
```

## Development

To modify the model or add features:

1. Edit `mbti_service.py`
2. Update `requirements_service.txt` if needed
3. Rebuild container: `docker build -t mbti-service .`
4. Test changes: `python test_mbti_service.py`

## License

This service is part of the KundaliMatch aligned-recommender system. 