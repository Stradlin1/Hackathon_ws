# Lost & Found:  Intelligent Item Matching with CLIP

## Overview

This project implements an intelligent lost and found system that leverages CLIP (Contrastive Language-Image Pre-training) for semantic image-text matching. The application enables users to report lost or found items and automatically matches them using multimodal embeddings, making it easier to reunite people with their belongings.

Originally developed as a lost-and-found hackathon prototype in 2024.

Source of the adapted prototype: https://github.com/vstrozzi/hackathon-image-finder-tool-CLIP

The project uses third-party libraries subject to their respective licenses. Attribution to the source project is retained; sample accounts and credentials should not be committed.

## Abstract

Traditional lost and found systems rely on manual keyword searches and visual browsing, making it difficult to match items efficiently. This project addresses this challenge by implementing a semantic matching system powered by CLIP embeddings. 

The system analyzes both images and textual descriptions of lost and found items, converting them into a shared embedding space where semantically similar items can be identified regardless of exact keyword matches. Users can upload images and descriptions of items they've lost or found, and the system automatically suggests potential matches based on visual and textual similarity.

The application is built with Streamlit for the frontend, uses SQLite for data persistence, and employs multilingual CLIP models to support diverse user descriptions.  This approach significantly reduces the time needed to reunite lost items with their owners.

## Key Features

* **Multimodal Matching:** Combines image and text embeddings using CLIP to find semantically similar items
* **User Authentication:** Secure login and registration system with session management
* **Intelligent Search:** Finds matches even when descriptions use different terminology
* **Location Awareness:** Integrates ETH Zurich location data for context
* **Real-time Notifications:** Alerts users when potential matches are found
* **Profile Management:** Users can track their lost and found items

## Architecture

### Core Components

* **Frontend (Streamlit):** State-machine based UI with multiple views: 
  - Login/Registration
  - Lost/Found item submission
  - Match viewing and confirmation
  - User profile management

* **Database Layer (`db_manager.py`):** SQLite-based persistence with tables for:
  - Items (with serialized images and embeddings)
  - Users
  - Lost/Found item associations
  - Match relationships

* **Embedding Engine:** CLIP-based semantic encoding: 
  - Image embeddings for visual similarity
  - Text embeddings for description matching
  - Multilingual support for diverse users

### Data Model

```
Item:  id, image, embedding, description, time, location
User: username, password, email
Matches: found_item_id ↔ lost_item_id
```

## Methods & Implementation

### CLIP-Based Matching

The system uses CLIP (Contrastive Language-Image Pre-training) to create unified embeddings for both images and text descriptions:

1. **Image Encoding:** Uploaded images are processed through CLIP's vision encoder
2. **Text Encoding:** Item descriptions are processed through CLIP's text encoder
3. **Similarity Computation:** Cosine similarity in the embedding space identifies potential matches
4. **Multilingual Support:** Sentence transformers enable description matching across languages

### State Machine Architecture

The application uses a state-based navigation system with the following states: 
- `login`: User authentication
- `register`: New user registration
- `lost_or_found`: Main menu for choosing action
- `lost`: Submit lost item report
- `found`: Submit found item report
- `profile`: View user's items and matches
- `this_your_item`: Confirm match for found items
- `this_description_matches`: Confirm match for lost items
- `someone_found`: Notification when someone found your item
- `someone_lost`: Notification when someone lost an item you found

## Project Structure

```
hackathon-image-finder-tool-CLIP/
├── state/                          # State management modules
│   ├── login.py
│   ├── register.py
│   ├── lost_or_found.py
│   ├── lost.py
│   ├── found.py
│   ├── profile.py
│   ├── this_your_item. py
│   ├── this_description_matches.py
│   ├── someone_found. py
│   └── someone_lost.py
├── static/                         # Static assets (logo, images)
├── sentence_transformers/          # Transformer models for embeddings
├── app.py                          # Main Streamlit application
├── db_manager.py                   # Database management classes
├── reset_db.py                     # Database reset utility
├── config_auth.yaml                # Authentication configuration
├── rooms.json                      # ETH location data
├── items.db                        # SQLite database (generated)
└── Image_Search-multilingual.ipynb # CLIP experimentation notebook
```

## Installation & Setup

### Prerequisites

**Conda Environment:**
```bash
conda create -n lost-found python=3.9
conda activate lost-found
```

**Conda Dependencies:**
```bash
conda install streamlit numpy matplotlib pillow scikit-learn
conda install conda-forge::transformers
conda install pytorch torchvision torchaudio cpuonly -c pytorch
```

**Pip Dependencies:**
```bash
pip install streamlit_authenticator streamlit_folium streamlit_extras
```

### Model Setup

#### CLIP (Recommended)
Use Hugging Face transformers (already included in conda dependencies):
```python
from transformers import CLIPProcessor, CLIPModel
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
```

#### Alternative: MiniCPM (CPU-only vision-language model)
For detailed image descriptions: 
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && make
```
Follow the tutorial at https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf

**Example prompt:**
```
Analyze the image and identify the main object. Provide a detailed and objective 
description of its physical features, focusing on visible attributes such as text, 
colors, shapes, dimensions... 
```

## Running the Application

### Environment Setup

**Windows:**
```powershell
$env:STREAMLIT_SERVER_ENABLE_STATIC_SERVING = 'true'
```

**Linux/Mac:**
```bash
export STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true
```

### Launch

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

### Database Management

To reset the database:
```bash
python reset_db.py
```

## Usage Workflow

### Reporting a Lost Item
1. Log in or register
2. Select "I lost something"
3. Upload an image (if available) or provide a description
4. Specify location and time
5. System automatically searches for matching found items

### Reporting a Found Item
1. Log in or register
2. Select "I found something"
3. Upload image and description
4. Specify location and time
5. System notifies users with matching lost items

### Viewing Matches
1. Navigate to profile
2. View potential matches for your items
3. Confirm or reject matches
4. Contact information becomes available upon mutual confirmation

## Technical Highlights

* **Efficient Embedding Storage:** Embeddings are serialized with pickle and stored as BLOBs in SQLite
* **Session Management:** Streamlit authenticator handles secure session cookies
* **Stylable UI:** Custom CSS styling for enhanced user experience
* **Join Queries:** Efficient SQL joins to retrieve matched items without redundancy
* **Unmatched Item Tracking:** Dedicated queries to find items still awaiting matches

## Future Enhancements

* **Similarity Threshold Tuning:** Adjustable matching sensitivity
* **Multi-image Support:** Multiple angles per item
* **Real-time Notifications:** Push notifications for new matches
* **Advanced Filters:** Filter by date range, location proximity, category
* **Mobile Application:** Native mobile app for easier on-the-go reporting
* **Integration with Campus Systems:** Connect with campus security databases

## Acknowledgments

Developed during the ETH Zurich Hackathon 2024 using open-source technologies: 
- OpenAI CLIP for multimodal embeddings
- Streamlit for rapid web app development
- SQLite for lightweight data persistence
- Hugging Face Transformers for model infrastructure
