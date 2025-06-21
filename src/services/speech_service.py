import speech_recognition as sr
import os
import tempfile
from pydub import AudioSegment
from typing import Optional, Dict, Any

class SpeechService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Initialize microphone only when needed to avoid PyAudio dependency issues
        self.microphone = None

    def transcribe_audio_file(self, audio_file_path: str, language: str = 'en') -> Dict[str, Any]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path: Path to the audio file
            language: Language code ('en' for English, 'ar' for Arabic)
            
        Returns:
            Dictionary with transcription result and confidence
        """
        try:
            # Convert audio to WAV format if needed
            audio_wav_path = self._convert_to_wav(audio_file_path)
            
            # Load audio file
            with sr.AudioFile(audio_wav_path) as source:
                audio_data = self.recognizer.record(source)
            
            # Set language code for recognition
            language_code = 'ar-SA' if language == 'ar' else 'en-US'
            
            # Perform speech recognition
            try:
                text = self.recognizer.recognize_google(audio_data, language=language_code)
                return {
                    'success': True,
                    'text': text,
                    'confidence': 0.8,  # Google doesn't provide confidence, so we use a default
                    'language': language
                }
            except sr.UnknownValueError:
                return {
                    'success': False,
                    'error': 'Could not understand audio',
                    'text': '',
                    'confidence': 0.0,
                    'language': language
                }
            except sr.RequestError as e:
                return {
                    'success': False,
                    'error': f'Speech recognition service error: {e}',
                    'text': '',
                    'confidence': 0.0,
                    'language': language
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Audio processing error: {e}',
                'text': '',
                'confidence': 0.0,
                'language': language
            }
        finally:
            # Clean up temporary files
            if 'audio_wav_path' in locals() and audio_wav_path != audio_file_path:
                try:
                    os.remove(audio_wav_path)
                except:
                    pass

    def _convert_to_wav(self, audio_file_path: str) -> str:
        """
        Convert audio file to WAV format for speech recognition
        
        Args:
            audio_file_path: Path to the input audio file
            
        Returns:
            Path to the converted WAV file
        """
        try:
            # Check if file is already WAV
            if audio_file_path.lower().endswith('.wav'):
                return audio_file_path
            
            # Load audio file with pydub
            audio = AudioSegment.from_file(audio_file_path)
            
            # Convert to WAV format
            temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            audio.export(temp_wav.name, format='wav')
            temp_wav.close()
            
            return temp_wav.name
            
        except Exception as e:
            print(f"Error converting audio to WAV: {e}")
            return audio_file_path

    def transcribe_live_audio(self, duration: int = 5, language: str = 'en') -> Dict[str, Any]:
        """
        Transcribe live audio from microphone
        
        Args:
            duration: Recording duration in seconds
            language: Language code ('en' for English, 'ar' for Arabic)
            
        Returns:
            Dictionary with transcription result and confidence
        """
        try:
            # Set language code for recognition
            language_code = 'ar-SA' if language == 'ar' else 'en-US'
            
            with self.microphone as source:
                print(f"Recording for {duration} seconds...")
                audio_data = self.recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
            
            # Perform speech recognition
            try:
                text = self.recognizer.recognize_google(audio_data, language=language_code)
                return {
                    'success': True,
                    'text': text,
                    'confidence': 0.8,
                    'language': language
                }
            except sr.UnknownValueError:
                return {
                    'success': False,
                    'error': 'Could not understand audio',
                    'text': '',
                    'confidence': 0.0,
                    'language': language
                }
            except sr.RequestError as e:
                return {
                    'success': False,
                    'error': f'Speech recognition service error: {e}',
                    'text': '',
                    'confidence': 0.0,
                    'language': language
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Microphone error: {e}',
                'text': '',
                'confidence': 0.0,
                'language': language
            }

    def save_audio_file(self, audio_data: bytes, file_path: str) -> bool:
        """
        Save audio data to file
        
        Args:
            audio_data: Raw audio data
            file_path: Path where to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            return True
        except Exception as e:
            print(f"Error saving audio file: {e}")
            return False

    def get_audio_duration(self, audio_file_path: str) -> float:
        """
        Get duration of audio file in seconds
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Duration in seconds, or 0 if error
        """
        try:
            audio = AudioSegment.from_file(audio_file_path)
            return len(audio) / 1000.0  # Convert milliseconds to seconds
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            return 0.0

    def validate_audio_quality(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Validate audio quality for speech recognition
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary with quality assessment
        """
        try:
            audio = AudioSegment.from_file(audio_file_path)
            
            # Basic quality checks
            duration = len(audio) / 1000.0
            sample_rate = audio.frame_rate
            channels = audio.channels
            
            # Quality assessment
            quality_score = 1.0
            issues = []
            
            if duration < 1.0:
                quality_score -= 0.3
                issues.append("Audio too short")
            
            if sample_rate < 16000:
                quality_score -= 0.2
                issues.append("Low sample rate")
            
            if channels > 2:
                quality_score -= 0.1
                issues.append("Too many channels")
            
            # Check for silence
            if audio.dBFS < -40:
                quality_score -= 0.3
                issues.append("Audio too quiet")
            
            quality_score = max(0.0, quality_score)
            
            return {
                'quality_score': quality_score,
                'duration': duration,
                'sample_rate': sample_rate,
                'channels': channels,
                'volume_db': audio.dBFS,
                'issues': issues,
                'suitable_for_recognition': quality_score > 0.5
            }
            
        except Exception as e:
            return {
                'quality_score': 0.0,
                'duration': 0.0,
                'sample_rate': 0,
                'channels': 0,
                'volume_db': -100,
                'issues': [f"Error analyzing audio: {e}"],
                'suitable_for_recognition': False
            }

