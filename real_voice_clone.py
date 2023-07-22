# -*- coding: utf-8 -*-
"""fimima_voice_clone.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1R_veQ1Mh5mqtKq4k7lPfdZxhsKRioQiz

# Bark text-to-speech voice cloning.
Clone voices to create speaker history prompt files (.npz) for [bark text-to-speech](https://github.com/suno-ai/bark).
(This version of the notebook is made to work on Google Colab, make sure your runtime hardware accelerator is set to GPU)

# Google Colab: Clone the repository
"""

# Commented out IPython magic to ensure Python compatibility.
!git clone https://github.com/gitmylo/bark-voice-cloning-HuBERT-quantizer/
# %cd bark-voice-cloning-HuBERT-quantizer

"""## Install packages"""

# Commented out IPython magic to ensure Python compatibility.
# %pip install fairseq
# %pip install tensorboardX
# %pip install audiolm_pytorch
# %pip install bark
# %pip install -r requirements.txt
# %pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117

from bark.generation import load_codec_model, SAMPLE_RATE, preload_models, codec_decode, generate_coarse, generate_fine, generate_text_semantic
from bark.api import generate_audio
from transformers import BertTokenizer
from encodec.utils import convert_audio
from encodec import EncodecModel
from encodec.utils import convert_audio
import numpy as np
import torch
import torchaudio

device = 'cuda' # or 'cpu'
model = load_codec_model(use_gpu=True if device == 'cuda' else False)

"""## Load models"""

#From https://github.com/gitmylo/bark-voice-cloning-HuBERT-quantizer
from bark_hubert_quantizer.hubert_manager import HuBERTManager
hubert_manager = HuBERTManager()
hubert_manager.make_sure_hubert_installed()
hubert_manager.make_sure_tokenizer_installed()

# From https://github.com/gitmylo/bark-voice-cloning-HuBERT-quantizer
# Load bark_hubert_quantizer for semantic tokens
from bark_hubert_quantizer.pre_kmeans_hubert import CustomHubert
from bark_hubert_quantizer.customtokenizer import CustomTokenizer

# Load the HuBERT model
hubert_model = CustomHubert(checkpoint_path='data/models/hubert/hubert.pt').to(device)

# Load the CustomTokenizer model
tokenizer = CustomTokenizer.load_from_checkpoint('data/models/hubert/tokenizer.pth').to(device)

"""## Load wav and create speaker history prompt"""

# Load and pre-process the audio waveform
audio_filepath = '/content/input.wav' # the audio you want to clone
wav, sr = torchaudio.load(audio_filepath)
wav = convert_audio(wav, sr, model.sample_rate, model.channels)
wav = wav.to(device)

semantic_vectors = hubert_model.forward(wav, input_sample_hz=model.sample_rate)
semantic_tokens = tokenizer.get_token(semantic_vectors)

# Extract discrete codes from EnCodec
with torch.no_grad():
    encoded_frames = model.encode(wav.unsqueeze(0))
codes = torch.cat([encoded[0] for encoded in encoded_frames], dim=-1).squeeze()  # [n_q, T]

# move codes to cpu
codes = codes.cpu().numpy()
# move semantic tokens to cpu
semantic_tokens = semantic_tokens.cpu().numpy()

voice_name = 'output' # whatever you want the name of the voice to be
output_path = '/content/' + voice_name + '.npz'
history_prompt = output_path
np.savez(output_path, fine_prompt=codes, coarse_prompt=codes[:2, :], semantic_prompt=semantic_tokens)

# Enter your prompt and speaker here
text_prompt = "Education is the process of facilitating learning, or the acquisition of knowledge, skills, values, beliefs, and habits. Educational methods include teaching, training, storytelling, discussion, and directed research."

# download and load all models
preload_models(
    text_use_gpu=True,
    text_use_small=False,
    coarse_use_gpu=True,
    coarse_use_small=False,
    fine_use_gpu=True,
    fine_use_small=False,
    codec_use_gpu=True,
    force_reload=False,
    # path="models"
)

x_semantic = generate_text_semantic(
    text_prompt,
    history_prompt,
    temp=0.7,
    top_k=50,
    top_p=0.95,
)

x_coarse_gen = generate_coarse(
    x_semantic,
    history_prompt,
    temp=0.7,
    top_k=50,
    top_p=0.95,
)
x_fine_gen = generate_fine(
    x_coarse_gen,
    history_prompt,
    temp=0.5,
)
audio_array = codec_decode(x_fine_gen)

from IPython.display import Audio
# play audio
Audio(audio_array, rate=SAMPLE_RATE)

from scipy.io.wavfile import write as write_wav
from google.colab import files
# save audio
filepath = '/content/' + 'output' + '.wav' # change this to your desired output path
write_wav(filepath, SAMPLE_RATE, audio_array)
files.download(filepath)