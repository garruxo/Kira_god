# -*- coding: utf-8 -*-
"""
afinar_lora.py - Ajuste fino (LoRA) del cerebro de Kira con TUS mejoras, en un PC con tarjeta gráfica o en Google Colab.

  1. En el móvil: «Kira, prepara datos de entrenamiento y guárdalos en descargas»  -> Descargas/Kira/kira_mejoras.jsonl
  2. Aquí (Colab: Entorno de ejecución › GPU T4, gratis):
         pip install torch transformers peft accelerate
         python afinar_lora.py kira_mejoras.jsonl --modelo Qwen/Qwen3.5-2B      (el MISMO que usa tu móvil: ligero = 2B,
                                                                                 listo = 4B)
     Sale la carpeta  kira_lora/  (el adaptador, unos MB).
  3. Convertirlo a GGUF con llama.cpp:
         git clone https://github.com/ggml-org/llama.cpp && pip install -r llama.cpp/requirements.txt
         python llama.cpp/convert_lora_to_gguf.py kira_lora --base-model-id Qwen/Qwen3.5-2B --outfile kira_lora.gguf
  4. Súbelo a algún sitio con enlace directo (Hugging Face, Drive «cualquiera con el enlace», GitHub…) y en el móvil:
         «Kira, instala mi ajuste: <enlace>»

Sincero: este script NO se ha probado en este proyecto (hace falta una GPU y los modelos originales, que no estaban
disponibles al escribirlo). Si el modelo de Hugging Face tiene otra arquitectura (los Qwen3.5 traen visión), puede que
haya que cambiar la clase de carga o los módulos de destino (--capas). Con pocos ejemplos (cientos), 1-3 épocas
bastan; más, y el modelo empieza a repetir de memoria (sobreajuste).
"""
import argparse
import json
import math
import os
import random


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        filas = [json.loads(l) for l in f if l.strip()]
    return [x["messages"] for x in filas if x.get("messages")]


def main():
    ap = argparse.ArgumentParser(description="Ajuste fino LoRA del cerebro de Kira")
    ap.add_argument("datos", help="kira_mejoras.jsonl (lo prepara Kira)")
    ap.add_argument("--modelo", default="Qwen/Qwen3.5-2B", help="el modelo base de Hugging Face (el mismo del móvil)")
    ap.add_argument("--salida", default="kira_lora")
    ap.add_argument("--epocas", type=float, default=2.0)
    ap.add_argument("--rango", type=int, default=16, help="r del LoRA (8-32)")
    ap.add_argument("--ritmo", type=float, default=2e-4)
    ap.add_argument("--largo", type=int, default=2048, help="fichas máximas por ejemplo")
    ap.add_argument("--capas", default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    a = ap.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    conversaciones = leer(a.datos)
    random.Random(0).shuffle(conversaciones)
    n_prueba = max(1, len(conversaciones) // 10)
    prueba, entreno = conversaciones[:n_prueba], conversaciones[n_prueba:]
    print(f"{len(entreno)} ejemplos para entrenar y {len(prueba)} para comprobar")

    tok = AutoTokenizer.from_pretrained(a.modelo)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(a.modelo, torch_dtype=torch.bfloat16 if torch.cuda.is_available()
                                                  else torch.float32, device_map="auto")
    modelo = get_peft_model(modelo, LoraConfig(r=a.rango, lora_alpha=2 * a.rango, lora_dropout=0.05,
                                               target_modules=a.capas.split(","), task_type="CAUSAL_LM"))
    modelo.print_trainable_parameters()

    def codificar(mensajes):
        """Solo se aprende la RESPUESTA (lo del asistente), no a repetir la pregunta."""
        previo = tok.apply_chat_template(mensajes[:-1], tokenize=False, add_generation_prompt=True)
        todo = previo + mensajes[-1]["content"] + (tok.eos_token or "")
        ids = tok(todo, truncation=True, max_length=a.largo)["input_ids"]
        n_previo = len(tok(previo, truncation=True, max_length=a.largo)["input_ids"])
        etiquetas = [-100] * n_previo + ids[n_previo:]
        return torch.tensor([ids]), torch.tensor([etiquetas[:len(ids)]])

    opt = torch.optim.AdamW([p for p in modelo.parameters() if p.requires_grad], lr=a.ritmo)
    pasos = int(math.ceil(len(entreno) * a.epocas))
    modelo.train()
    for paso in range(pasos):
        ids, etiq = codificar(entreno[paso % len(entreno)])
        perdida = modelo(input_ids=ids.to(modelo.device), labels=etiq.to(modelo.device)).loss
        perdida.backward()
        torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
        opt.step()
        opt.zero_grad()
        if paso % 20 == 0 or paso == pasos - 1:
            print(f"paso {paso + 1}/{pasos}: pérdida {perdida.item():.3f}")
    modelo.eval()
    with torch.no_grad():
        media = sum(modelo(input_ids=i.to(modelo.device), labels=e.to(modelo.device)).loss.item()
                    for i, e in map(codificar, prueba)) / len(prueba)
    print(f"Pérdida en los ejemplos de comprobación: {media:.3f} (más baja = mejor; si sube mucho, menos épocas)")
    modelo.save_pretrained(a.salida)
    tok.save_pretrained(a.salida)
    print(f"Listo: {os.path.abspath(a.salida)}. Ahora conviértelo a GGUF (paso 3 de arriba).")


if __name__ == "__main__":
    main()
