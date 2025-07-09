import google.generativeai as genai
import os
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.model = None
        self.is_initialized = False
        # Try multiple ways to get the API key
        self.api_key = (
            os.getenv('GEMINI_API_KEY') or 
            settings.gemini_api_key or 
            None
        )
        # Cache health status to avoid quota consumption
        self._last_health_check = None
        self._health_check_cache_ttl = 300  # 5 minutes
        self._last_health_check_time = 0
        
    async def initialize(self):
        """Initialize Gemini service"""
        try:
            if not self.api_key:
                logger.error("❌ GEMINI_API_KEY not found in environment variables or settings")
                logger.error("❌ Checked: os.getenv('GEMINI_API_KEY') and settings.gemini_api_key")
                return False
                
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.is_initialized = True
            logger.info("✅ Gemini 2.0 Flash initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {str(e)}")
            self.is_initialized = False
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Gemini service health with caching to avoid quota consumption"""
        current_time = datetime.utcnow().timestamp()
        
        # Return cached result if available and not expired
        if (self._last_health_check and 
            current_time - self._last_health_check_time < self._health_check_cache_ttl):
            logger.info("🔄 Returning cached health status to save quota")
            return self._last_health_check
        
        if not self.api_key:
            result = {
                "status": "error",
                "model": "gemini-2.0-flash-exp",
                "message": "API key not configured",
                "api_key_configured": False,
                "api_key_status": "missing"
            }
            self._cache_health_result(result, current_time)
            return result
        
        if not self.is_initialized:
            result = {
                "status": "error", 
                "model": "gemini-2.0-flash-exp",
                "message": "Service not initialized",
                "api_key_configured": True,
                "api_key_status": "configured"
            }
            self._cache_health_result(result, current_time)
            return result
            
        # For initialized service, return optimistic status without API call
        # Only do actual API test if specifically requested
        result = {
            "status": "ready",
            "model": "gemini-2.0-flash-exp", 
            "message": "Initialized and ready (quota-preserving mode)",
            "api_key_configured": True,
            "api_key_status": "configured",
            "quota_preserved": True
        }
        
        self._cache_health_result(result, current_time)
        return result
    
    def _cache_health_result(self, result: Dict[str, Any], timestamp: float):
        """Cache health check result"""
        self._last_health_check = result
        self._last_health_check_time = timestamp
    
    async def test_api_connection(self) -> Dict[str, Any]:
        """Actually test API connection - only call when needed"""
        if not self.is_initialized:
            return {
                "status": "error",
                "message": "Service not initialized"
            }
            
        try:
            # This is the only method that should actually consume quota
            logger.info("🧪 Testing Gemini API connection (consuming quota)")
            response = self.model.generate_content("Say 'test'")
            return {
                "status": "online",
                "model": "gemini-2.0-flash-exp", 
                "message": "API connection successful",
                "api_test": "passed"
            }
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                return {
                    "status": "quota_exceeded",
                    "model": "gemini-2.0-flash-exp",
                    "message": f"Quota exceeded: {error_msg}",
                    "api_test": "failed"
                }
            else:
                return {
                    "status": "error",
                    "model": "gemini-2.0-flash-exp", 
                    "message": f"Connection error: {error_msg}",
                    "api_test": "failed"
                }

    async def generate_schema_from_natural_language(
        self,
        description: str,
        domain: str = 'general',
        data_type: str = 'tabular'
    ) -> Dict[str, Any]:
        """Generate schema from natural language description"""
        logger.info("🧠 Using Gemini 2.0 Flash for schema generation...")
        
        if not self.is_initialized:
            raise Exception("Gemini service not initialized")

        prompt = f"""
        Based on this natural language description, generate a detailed database schema:
        
        Description: "{description}"
        Domain: {domain}
        Data Type: {data_type}
        
        Please create a comprehensive schema with:
        1. Realistic field names that match the described data
        2. Appropriate data types (string, number, boolean, date, email, phone, etc.)
        3. Constraints where applicable (min/max values, required fields)
        4. Sample values or examples for each field
        5. Domain-specific field suggestions
        
        Return the response as JSON with this exact structure:
        {{
            "schema": {{
                "field_name": {{
                    "type": "string|number|boolean|date|datetime|email|phone|uuid|text",
                    "description": "Clear description of the field",
                    "constraints": {{
                        "min": number,
                        "max": number,
                        "required": boolean,
                        "unique": boolean
                    }},
                    "examples": ["example1", "example2", "example3"]
                }}
            }},
            "detected_domain": "detected_domain_from_description",
            "estimated_rows": number,
            "relationships": ["description of data relationships"],
            "suggestions": ["suggestions for data generation"]
        }}
        
        Make sure the schema is realistic and comprehensive for: {description}
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            # Clean up the response
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1]
            
            text = text.strip()
            parsed = json.loads(text)
            
            logger.info(f"✅ Gemini generated schema with {len(parsed.get('schema', {}))} fields")
            
            return {
                'schema': parsed.get('schema', {}),
                'detected_domain': parsed.get('detected_domain', domain),
                'estimated_rows': parsed.get('estimated_rows', 10000),
                'relationships': parsed.get('relationships', []),
                'suggestions': parsed.get('suggestions', [])
            }
            
        except Exception as e:
            logger.error(f"❌ Schema generation failed: {str(e)}")
            raise e

    async def generate_synthetic_data(
        self,
        schema: Dict[str, Any],
        config: Dict[str, Any],
        description: str = "",
        source_data: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate synthetic data using Gemini"""
        logger.info("🤖 Generating synthetic data with Gemini 2.0 Flash...")
        
        if not self.is_initialized:
            raise Exception("Gemini service not initialized")

        row_count = config.get('rowCount', 100)
        
        prompt = f"""
        Generate {row_count} rows of realistic synthetic data based on this schema:
        
        Schema: {json.dumps(schema, indent=2)}
        Description: "{description}"
        Configuration: {json.dumps(config, indent=2)}
        
        Generate data that:
        1. Follows the exact schema structure
        2. Uses realistic values for each field type
        3. Maintains data relationships and constraints
        4. Ensures variety and realistic distribution
        5. Follows domain-specific patterns when applicable
        
        Return as a JSON array of {row_count} objects with the exact field names from the schema.
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            # Clean and parse JSON
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1]
            
            text = text.strip()
            data = json.loads(text)
            
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"✅ Generated {len(data)} synthetic records with Gemini")
                return data[:row_count]
            else:
                raise Exception("Invalid data format returned from Gemini")
                
        except Exception as e:
            logger.error(f"❌ Synthetic data generation failed: {str(e)}")
            raise e

    async def analyze_schema_advanced(
        self,
        sample_data: List[Dict[str, Any]],
        config: Dict[str, Any],
        source_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Advanced schema analysis"""
        if not self.is_initialized:
            return {
                "domain": "general",
                "data_types": {},
                "relationships": [],
                "quality_score": 85,
                "pii_detected": False
            }

        prompt = f"""
        Analyze this dataset and provide comprehensive insights:
        Sample Data: {json.dumps(sample_data[:5], indent=2)}
        
        Provide analysis including:
        1. Detected domain (healthcare, finance, retail, etc.)
        2. Data types for each field
        3. Potential relationships between fields
        4. Quality assessment
        5. PII detection
        6. Suggestions for improvement
        
        Return as JSON with structure:
        {{
            "domain": "detected_domain",
            "data_types": {{}},
            "relationships": [],
            "quality_score": number,
            "pii_detected": boolean,
            "suggestions": []
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"❌ Schema analysis failed: {str(e)}")
            return {
                "domain": "general",
                "data_types": {},
                "relationships": [],
                "quality_score": 85,
                "pii_detected": False,
                "error": str(e)
            }

    async def assess_privacy_risks(
        self,
        data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess privacy risks in data"""
        if not self.is_initialized:
            return {
                "privacy_score": 90,
                "pii_detected": [],
                "sensitive_attributes": [],
                "risk_level": "low",
                "recommendations": ["Gemini service not available for privacy analysis"]
            }

        prompt = f"""
        Assess privacy risks in this dataset:
        Data Sample: {json.dumps(data[:3], indent=2)}
        
        Check for:
        1. PII (Personally Identifiable Information)
        2. Sensitive attributes
        3. Re-identification risks
        4. Data linkage possibilities
        
        Return as JSON:
        {{
            "privacy_score": number_0_to_100,
            "pii_detected": ["list of detected PII fields"],
            "sensitive_attributes": ["list of sensitive fields"],
            "risk_level": "low|medium|high",
            "recommendations": ["privacy improvement suggestions"]
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"❌ Privacy assessment failed: {str(e)}")
            return {
                "privacy_score": 85,
                "pii_detected": [],
                "sensitive_attributes": [],
                "risk_level": "medium",
                "recommendations": [f"Privacy analysis error: {str(e)}"]
            }

    async def switch_model(self, model_name: str) -> Dict[str, Any]:
        """Switch to a different Gemini model to avoid quota issues"""
        logger.info(f"🔄 Switching to model: {model_name}")
        
        if not self.api_key:
            return {
                "status": "error",
                "message": "API key not configured",
                "current_model": None,
                "new_model": model_name
            }
        
        try:
            # List of available models to try
            available_models = [
                "gemini-1.5-flash",
                "gemini-1.5-pro", 
                "gemini-2.0-flash-exp",
                "gemini-1.0-pro"
            ]
            
            if model_name not in available_models:
                return {
                    "status": "error",
                    "message": f"Model {model_name} not available. Available models: {available_models}",
                    "current_model": getattr(self.model, 'model_name', None),
                    "new_model": model_name
                }
            
            # Configure new model
            old_model = getattr(self.model, 'model_name', 'unknown') if self.model else 'none'
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
            
            # Clear health check cache to force revalidation
            self._last_health_check = None
            self._last_health_check_time = 0
            
            logger.info(f"✅ Successfully switched from {old_model} to {model_name}")
            
            return {
                "status": "success",
                "message": f"Successfully switched to {model_name}",
                "previous_model": old_model,
                "current_model": model_name,
                "available_models": available_models
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to switch model: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to switch model: {str(e)}",
                "current_model": getattr(self.model, 'model_name', None),
                "new_model": model_name
            }
