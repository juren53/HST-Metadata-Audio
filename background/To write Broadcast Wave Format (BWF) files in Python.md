## To write Broadcast Wave Format (BWF) files in Python.md

To write Broadcast Wave Format (BWF) files in Python, you should use the dedicated wave-bwf-rf64 library, as the standard wave module does not support the required BWF metadata chunks. 
GitHub
GitHub
 +3
Using the wave-bwf-rf64 library 
The wave-bwf-rf64 package is an extension of Python's standard wave module that adds support for BWF-specific metadata chunks like bext, axml, chna, MD5, and levl, as well as the RF64 format for files larger than 4GB. 
GitHub
GitHub
 +1
Installation
Install the library using pip: 
bash
pip install wave-bwf-rf64
Example: Writing a BWF file with metadata
The process is similar to using the standard wave module, but you can access and write the BWF-specific chunks. 
python
import contextlib
import wave_bwf_rf64
import numpy as np

# Audio parameters (example: mono, 48000 Hz, 16-bit PCM)
sample_rate = 48000
channels = 1
sample_width_bytes = 2 # 16 bits
duration_seconds = 5
num_frames = sample_rate * duration_seconds

# Generate some sample audio data (e.g., a simple sine wave)
# Amplitude must be within the range for 16-bit PCM
max_amplitude = 32767
t = np.linspace(0., duration_seconds, num_frames, endpoint=False)
audio_data_float = max_amplitude * np.sin(2 * np.pi * 440 * t) # 440 Hz sine wave
audio_data_int16 = audio_data_float.astype(np.int16)
# Convert to bytes
raw_frames = audio_data_int16.tobytes()

# Write the BWF file with the 'bext' chunk
try:
    with contextlib.closing(wave_bwf_rf64.open("output_bwf.wav", "wb")) as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width_bytes)
        wf.setframerate(sample_rate)
        
        # Add BWF metadata ('bext' chunk)
        # The library provides a simple interface to the bext chunk
        wf.bwf_bext_description = "A test BWF file created with Python"
        wf.bwf_bext_originator = "My Python Script"
        wf.bwf_bext_originationDate = "2026-03-10"
        wf.bwf_bext_originationTime = "19:59:00"
        # UMID and other fields can also be set
        
        wf.writeframes(raw_frames)
    print("Successfully wrote BWF file output_bwf.wav")

except wave_bwf_rf64.Error as e:
    print(f"Error writing BWF file: {e}")
Key BWF metadata fields 
The bext (Broadcast extension) chunk contains essential metadata for broadcast production: 
EBU Technology & Innovation
EBU Technology & Innovation
 +1
description: A general description of the audio content.
originator: The name of the person or organization that created the file.
originationDate: The date of creation (YYYY-MM-DD).
originationTime: The time of creation (HH:MM:SS).
timeReference: A 64-bit integer specifying the time of the first sample relative to a time base (e.g., midnight), crucial for synchronization with other recordings. 
Wikipedia
Wikipedia
 +4

