echo "Cloning Repo..."
git clone https://github.com/Popeye68/TXT-EXTRACTOR
cd /TXT-EXTRACTOR
pip install -r requirements.txt
echo "Starting Bot..."
python -m Extractor
