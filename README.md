# 404NotFound — Multimodal Lost-and-Found Matching

404NotFound helps match a person's description of a lost object to photographs of found objects. It uses CLIP for cross-modal retrieval, BLIP for image descriptions, evidence-checked generative fingerprints, and information-gain-driven follow-up questions. Candidates are reranked after each response rather than being accepted solely on the basis of an initial similarity score.

## Capabilities

- **Multimodal search:** compares lost-item text to found-item photographs using aligned multilingual CLIP embeddings.
- **Generative item fingerprints:** proposes structured features (category, color, material, shape, brand, distinctive marks) from reports and generated image captions. A lightweight local text model can propose values; only values supported by the report or caption are accepted. If model weights are unavailable, deterministic feature extraction is used.
- **Active clarification:** measures the information gain of available candidate attributes and asks one open-ended question at a time without disclosing candidate-specific answers.
- **Dynamic ranking:** combines cross-modal semantic similarity with positive and contradictory feature evidence. Unreported features remain neutral.
- **Mutual match confirmation:** lets one account send a match request; the other account must accept before either account can view contact information.
- **Local item history:** stores images, reports, fingerprints, and requests in SQLite.

## How matching works

1. A user reports a lost item by describing it, or reports a found item by uploading a photograph and reviewing an automatically generated caption.
2. BLIP produces a caption for a found-item photograph. The text model (`google/flan-t5-small` by default) attempts to propose fingerprint fields; the extractor keeps only fields with explicit supporting evidence. No missing attribute is guessed.
3. CLIP (`sentence-transformers/clip-ViT-B-32`) encodes found-item photographs. The aligned multilingual text model (`sentence-transformers/clip-ViT-B-32-multilingual-v1`) encodes lost-item descriptions.
4. The top eight cross-modal candidates are reranked using the fingerprint's matching and conflicting properties. The displayed score is **not** an ownership probability.
5. If the leading candidates differ on an unknown attribute, the system selects a question using posterior-weighted attribute entropy (information gain). The user can answer or skip; rankings update immediately. At most four questions are asked.
6. Users can send a match request for a candidate. The other account can accept or reject it from the profile screen. Contact details appear only after acceptance.

Question wording is based on a safe template associated with the attribute chosen by the information-gain algorithm. It never reveals a candidate's distinctive marks as suggested answers.

## Repository layout

~~~text
.
├── app.py                          # Streamlit entry point and navigation
├── db_manager.py                   # Existing SQLite report storage
├── matching/
│   ├── fingerprint.py              # Generative feature proposals and verification
│   ├── models.py                   # Cached CLIP, multilingual CLIP, BLIP
│   ├── engine.py                   # Evidence-based reranking and active questions
│   ├── workflow.py                 # Cross-modal candidate retrieval
│   ├── storage.py                  # Structured fingerprint persistence
│   └── requests.py                 # Request approval and privacy controls
├── state/
│   ├── found.py                    # Found-item submission
│   ├── lost.py                     # Lost-item submission
│   ├── interactive_match.py        # Follow-up questions and live ranking
│   ├── profile.py                  # Reports and match request handling
│   └── ...                         # Authentication and navigation
├── config_auth.example.yaml       # Local account configuration example
├── rooms.json                     # Location choices
├── reset_db.py                     # Populate synthetic sample data (destructive)
├── tests/                          # Local algorithm and data-flow tests
├── requirements.txt
└── requirements-dev.txt
~~~

## Installation

Use **Python 3.10 or 3.11** for the recommended local setup. The first run requires downloading pretrained model weights and may be slow on a CPU.

~~~bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
~~~

Copy the authentication template to a locally ignored configuration file:

~~~bash
# Linux / macOS
cp config_auth.example.yaml config_auth.yaml
# Windows PowerShell: Copy-Item config_auth.example.yaml config_auth.yaml
~~~

Edit `config_auth.yaml`. Replace the demonstration account's password with a bcrypt **hash**, use a real local test account, and replace `cookie.key` with a new random value. Two sample commands:

~~~bash
python -c "import bcrypt; print(bcrypt.hashpw(b'choose-a-test-password', bcrypt.gensalt()).decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
~~~

To create synthetic example records (optional):

~~~bash
python reset_db.py
~~~

**Caution:** `reset_db.py` deletes the existing `items.db` database. Do not execute it if you need to keep earlier reports or match requests.

Run the app:

~~~bash
streamlit run app.py
~~~

Open `http://localhost:8501`. Sign in or register, file a lost or found item report, answer the discriminative questions when offered, and review the ranked candidates. Send a request for the desired candidate and sign in to the other account to accept it under **My items and requests**.

## Configuration and offline behavior

`FINGERPRINT_TEXT_MODEL` controls the optional local text generator. It defaults to `google/flan-t5-small`; set it to `off` to skip the text generator and keep the rule-based extraction:

~~~bash
# Linux / macOS
export FINGERPRINT_TEXT_MODEL=off
# Windows PowerShell: $env:FINGERPRINT_TEXT_MODEL='off'
~~~

The text generator can improve structured proposals but is not required for the matching and question-selection algorithm. BLIP and the CLIP image/text encoders require their pretrained weights for full image-based matching. The first use of those functions downloads the weights through their respective Python libraries. If BLIP image captioning is unavailable, a manually entered description can be used instead.

## Tests

~~~bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app.py matching state
~~~

Tests include bilingual feature extraction, rejection of unsupported generated values, information-gain questions, reranking after answers, SQLite fingerprint migration, and two-party confirmation. Tests mock model embeddings so they can run without downloading model weights; **passing unit tests is not a substitute for an end-to-end run with installed models**.

## Privacy and limitations

- Authentication secrets and the SQLite database are local and excluded by `.gitignore`. Do not commit real user reports, personal photographs, or passwords.
- The image preprocessing path removes EXIF metadata and limits image dimensions before database storage.
- Pending requests do not reveal the other account's contact information. Contact information is visible after the receiving account accepts the request.
- The ranking metric and generated attributes are not proof of ownership. Generated suggestions require human review; current models may miss details or misinterpret photos.
- Time and location are recorded for reference but are **not** currently used in ranking or geographical filtering.
- The original database persists image arrays and embeddings using Python pickle. Treat `items.db` as trusted local data, not as an untrusted exchange format.
