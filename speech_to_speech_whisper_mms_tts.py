import gradio as gr
import numpy as np
import torch
from datasets import load_dataset

from transformers import VitsModel, VitsTokenizer, pipeline


device = "cuda:0" if torch.cuda.is_available() else "cpu"

# load speech translation checkpoint
asr_pipe = pipeline("automatic-speech-recognition", model="openai/whisper-base", device=device)

# load text-to-speech checkpoint and speaker embeddings
model = VitsModel.from_pretrained("facebook/mms-tts-vie")
tokenizer = VitsTokenizer.from_pretrained("facebook/mms-tts-vie")

embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)


def translate(audio):
    outputs = asr_pipe(audio, max_new_tokens=256, generate_kwargs={"task": "translate", "language": "vi"})
    return outputs["text"]


def synthesise(text):
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        output = model(inputs["input_ids"].to(device))
    speech = output.audio[0]
    return speech.cpu()


def speech_to_speech_translation(audio):
    translated_text = translate(audio)
    synthesised_speech = synthesise(translated_text)
    synthesised_speech = (synthesised_speech.numpy() * 32767).astype(np.int16)
    return 16000, synthesised_speech


title = "Cascaded STST"
description = """
Demo for cascaded speech-to-speech translation (STST), mapping from source speech in any language to target speech in Vietnamese.
Demo uses OpenAI's [Whisper Base](https://huggingface.co/openai/whisper-base) model for speech translation, and Meta's [MMS TTS](https://huggingface.co/facebook/mms-tts-deu) model for text-to-speech:

![Cascaded STST](https://huggingface.co/datasets/huggingface-course/audio-course-images/resolve/main/s2st_cascaded.png "Diagram of cascaded speech to speech translation")
"""

demo = gr.Blocks()

mic_translate = gr.Interface(
    fn=speech_to_speech_translation,
    inputs=gr.Audio(source="microphone", type="filepath"),
    outputs=gr.Audio(label="Generated Speech", type="numpy"),
    title=title,
    description=description,
)

file_translate = gr.Interface(
    fn=speech_to_speech_translation,
    inputs=gr.Audio(source="upload", type="filepath"),
    outputs=gr.Audio(label="Generated Speech", type="numpy"),
    examples=[["./example.wav"]],
    title=title,
    description=description,
)

with demo:
    gr.TabbedInterface([mic_translate, file_translate], ["Microphone", "Audio File"])

demo.launch()
