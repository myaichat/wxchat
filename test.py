import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import argparse

def load_prompter():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    prompter_model = AutoModelForCausalLM.from_pretrained("microsoft/Promptist",
                                                          cache_dir="cache").to(device)
    tokenizer = AutoTokenizer.from_pretrained("gpt2", cache_dir="cache")
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    return prompter_model, tokenizer, device

prompter_model, prompter_tokenizer, device = load_prompter()

def generate(plain_text):
    inputs = prompter_tokenizer(plain_text.strip() + " Rephrase:", return_tensors="pt", padding=True)
    input_ids = inputs.input_ids.to(device)
    attention_mask = inputs.attention_mask.to(device)
    eos_id = prompter_tokenizer.eos_token_id
    
    # Stream generation
    outputs = prompter_model.generate(input_ids, 
                                      attention_mask=attention_mask,
                                      do_sample=True,
                                      temperature=2.0, 
                                      max_new_tokens=500, 
                                      min_new_tokens=200, 
                                      num_beams=8, 
                                      top_k=50,
                                      top_p=0.95,
                                      num_return_sequences=4, 
                                      eos_token_id=eos_id, 
                                      pad_token_id=eos_id, 
                                      length_penalty=-2.0,
                                      repetition_penalty=5.0,
                                      return_dict_in_generate=True,
                                      output_scores=True)

    generated_tokens = outputs.sequences[:, input_ids.shape[-1]:]
    for seq_idx, seq in enumerate(generated_tokens):
        output_text = prompter_tokenizer.decode(seq, skip_special_tokens=True)
        print(f"\nSequence {seq_idx + 1}:\n{output_text}")

    res = prompter_tokenizer.decode(generated_tokens[0], skip_special_tokens=True).strip()
    return res

def main():
    prompt = """
    beautiful painting of a halo – wlop award winning photo portrait of ukrainian woman holding a bolt of bright color . sunflowers vapors holistic bespoke hyperdetailed volumetric lighting 4 k 8 k archviz demess stripmetro iridescent silky dappled stellar curvy radiating rainbow masses zdzisław william jhon dark craft providence trending on artstation cgsociety awards detailed intricate photorea. Ukrainian tryzub
    """
    
    optimized_prompt = generate(prompt)
    print("Optimized Prompt:")
    print(optimized_prompt)

if __name__ == "__main__":
    main()
