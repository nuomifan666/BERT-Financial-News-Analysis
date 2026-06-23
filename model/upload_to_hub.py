"""
上传训练好的模型到 Hugging Face Hub
运行前请先: pip install huggingface_hub
"""
import os
from huggingface_hub import HfApi, HfFolder, login

# ====== 改成你自己的 ======
HF_USERNAME = "nuomifan666"           # 你的 HF 用户名
MODEL_NAME = "bert-finance-sentiment" # 模型名字
LOCAL_MODEL_DIR = "model/saved"       # 本地模型路径
# =========================

# 先登录（需要 HF Access Token）
print("=" * 50)
print("请先去 https://huggingface.co/settings/tokens")
print("创建一个 Token（选 Write 权限），粘贴到下方")
print("=" * 50)

token = input("粘贴 Token: ").strip()
login(token=token)

# 上传模型
api = HfApi()
repo_id = f"{HF_USERNAME}/{MODEL_NAME}"

print(f"\n创建模型仓库: {repo_id}")
api.create_repo(repo_id=repo_id, exist_ok=True, repo_type="model")

print(f"上传模型中...")
api.upload_folder(
    folder_path=LOCAL_MODEL_DIR,
    repo_id=repo_id,
    repo_type="model",
)

print(f"\n✅ 上传完成！模型地址: https://huggingface.co/{repo_id}")
print(f"\n在 Space 中使用: model_name = '{repo_id}'")
