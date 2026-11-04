"""
audio_processor.py — Audio spectrogram generation for AI analysis.
"""
import os
import tempfile
import logging

import numpy as np
from scipy.io import wavfile
from scipy import signal
import matplotlib.pyplot as plt
from pydub import AudioSegment

from .exceptions import InvalidImageError, CorruptFileError, UnsupportedFormatError

logger = logging.getLogger(__name__)

def generate_spectrogram(file_path: str) -> str:
    """
    Reads an audio file, generates a spectrogram, and saves it as a temporary JPEG image.
    Returns the path to the generated image file.
    The caller is responsible for cleaning up the temporary file.
    """
    if not os.path.isfile(file_path):
        raise InvalidImageError(f"Audio file not found at path: {file_path}")

    # Create temporary WAV file if input is not WAV
    temp_wav_path = None
    try:
        # Pydub can read multiple formats
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_channels(1) # Mono
        
        fd, temp_wav_path = tempfile.mkstemp(suffix=".wav", prefix="deepguard_audio_")
        os.close(fd)
        audio.export(temp_wav_path, format="wav")
        
        sample_rate, samples = wavfile.read(temp_wav_path)
        
        if len(samples) == 0:
            raise CorruptFileError("Audio file contains no samples.")
            
        # Compute spectrogram
        frequencies, times, spectrogram = signal.spectrogram(samples, sample_rate)
        
        # Plot and save to image
        fd_img, img_path = tempfile.mkstemp(suffix=".jpg", prefix="deepguard_spectrogram_")
        os.close(fd_img)
        
        plt.figure(figsize=(4, 4)) # Keep it relatively small, e.g. 224x224 target
        plt.pcolormesh(times, frequencies, np.log10(spectrogram + 1e-10), shading='gouraud')
        plt.axis('off')
        
        plt.savefig(img_path, bbox_inches='tight', pad_inches=0)
        plt.close()
        
        return img_path
        
    except Exception as exc:
        raise CorruptFileError(f"Failed to process audio file: {exc}")
        
    finally:
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except OSError:
                pass
