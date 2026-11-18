"""GPU models used by the voice server."""
import re
import threading
import numpy as np
import torch
from transformers import AutoModelForCausalLM,AutoModelForMultimodalLM,AutoTokenizer,AutoProcessor
from local_choice import choose
from phone_context import complete_reply,needs_brief,needs_detail,phone_messages
from settings import ASR,DECISION,NAME

gate=threading.Lock()

class Models:
    def intent(self,text):
        with gate:return choose(self.chat,self.tok,text)[0]
    def __init__(self, local_controller=True):
        if local_controller:
            self.tok=AutoTokenizer.from_pretrained(DECISION)
            self.chat=AutoModelForCausalLM.from_pretrained(DECISION,dtype=torch.bfloat16).cuda().eval()
        path=ASR
        self.proc=AutoProcessor.from_pretrained(path)
        self.asr=AutoModelForMultimodalLM.from_pretrained(path,dtype=torch.bfloat16).cuda().eval()
    @torch.inference_mode()
    def transcribe(self,pcm):
        wave=np.frombuffer(pcm,'<i2').astype('float32')/32768
        if not len(wave) or np.sqrt(np.mean(wave**2))<.002:return ''
        with gate:
            inp=self.proc.apply_transcription_request(audio=wave,language='Chinese').to(self.asr.device,self.asr.dtype)
            out=self.asr.generate(**inp,max_new_tokens=100,do_sample=False)
            text=self.proc.decode(out[:,inp['input_ids'].shape[1]:],return_format='transcription_only')[0].strip()
            return re.sub(r'(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])','',text)
    @torch.inference_mode()
    def answer(self,text,history,phone=False):
        instruction='你是DeepseekChan，鲸语直播间的数字人。直接回应当前观众，参考这个观众刚才的对话，用自然中文说一到两句，尽量在35字内说完。'
        turns=[dict(role='system',content=instruction.replace('DeepseekChan',NAME))]
        for h in history[-4:]:turns.extend([dict(role='user',content=h['text']),dict(role='assistant',content=h['reply'])])
        turns.append(dict(role='user',content=text))
        if phone:turns=phone_messages(text,history)
        with gate:
            prompt=self.tok.apply_chat_template(turns,tokenize=False,add_generation_prompt=True)
            x=self.tok(prompt,return_tensors='pt').to(self.chat.device)
            brief=phone and needs_brief(text)
            limit=(256 if needs_detail(text) else 160) if phone and not brief else 60
            opts={'stop_strings':['。','！','？'],'tokenizer':self.tok} if brief else {}
            y=self.chat.generate(**x,max_new_tokens=limit,do_sample=False,pad_token_id=self.tok.eos_token_id,**opts)
            reply=self.tok.decode(y[0,x.input_ids.shape[1]:],skip_special_tokens=True).strip()
            return complete_reply(reply,y.shape[1]-x.input_ids.shape[1]==limit) if phone else reply[:160]
