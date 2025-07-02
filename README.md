# Narrador DF

Narrador en tiempo real para *Dwarf Fortress* que convierte el gamelog en
una historia hablada y en mensajes breves para el chat de tu stream.

## Instalación

```bash
git clone https://github.com/<TU-USUARIO>/narrador-df.git
cd narrador-df
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
copy config.example.toml config.toml   # y edita tu API key
python narrador_df.py
