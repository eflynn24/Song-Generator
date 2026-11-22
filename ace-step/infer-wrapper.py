import os
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from acestep.pipeline_ace_step import ACEStepPipeline


app = FastAPI(title="ACE-Step Song API")
pipeline = None


class GenerateRequest(BaseModel):
    prompt: str
    lyrics: str = ""
    infer_step: int = Field(default=27, ge=10, le=100)
    guidance_scale: float = Field(default=15.0, ge=1.0, le=30.0)
    output_path: str = "/app/outputs"
    seed: int = Field(default=12345, ge=0)


class GenerateResponse(BaseModel):
    status: str
    output_path: str


def get_pipeline() -> ACEStepPipeline:
    global pipeline
    if pipeline is None:
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        pipeline = ACEStepPipeline(
            checkpoint_dir="/app/checkpoints",
            dtype="bfloat16",
            torch_compile=False,
        )
    return pipeline


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    output_dir = Path(request.output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{uuid.uuid4().hex}.wav"

    model = get_pipeline()
    model(
        format="wav",
        prompt=request.prompt,
        lyrics=request.lyrics,
        infer_step=request.infer_step,
        guidance_scale=request.guidance_scale,
        scheduler_type="euler",
        cfg_type="apg",
        omega_scale=10.0,
        manual_seeds=[request.seed],
        guidance_interval=0.5,
        guidance_interval_decay=0.5,
        min_guidance_scale=3.0,
        use_erg_tag=True,
        use_erg_lyric=True,
        use_erg_diffusion=True,
        oss_steps="",
        guidance_scale_text=0.0,
        guidance_scale_lyric=0.0,
        save_path=str(output_file),
        batch_size=1,
    )

    return GenerateResponse(status="success", output_path=str(output_file))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
