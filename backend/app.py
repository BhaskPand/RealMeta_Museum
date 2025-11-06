import argparse
import base64
import hashlib
import io
import json
import os
import secrets
import uuid
from datetime import datetime
from functools import wraps
from typing import Dict, Any, List, Tuple

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image, ImageOps
import numpy as np
import imagehash
from sklearn.cluster import KMeans
import cv2


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

IMAGES_DIR = os.path.join(BASE_DIR, 'images')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
ARTWORKS_JSON = os.path.join(BASE_DIR, 'artworks.json')
EMBEDDINGS_JSON = os.path.join(BASE_DIR, 'embeddings.json')
ANALYTICS_LOG = os.path.join(BASE_DIR, 'analytics_log.json')


app = Flask(__name__)
CORS(app)


def load_artworks() -> Dict[str, Any]:
    if not os.path.exists(ARTWORKS_JSON):
        return {}
    with open(ARTWORKS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


ARTWORKS = load_artworks()


def safe_write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def preprocess_image_for_matching(pil_img: Image.Image, max_size: int = 512) -> Image.Image:
    """
    Preprocess image to normalize for better matching:
    - Auto-orient based on EXIF
    - Resize to consistent max dimension
    - Convert to RGB
    """
    try:
        # Auto-orient based on EXIF data
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass
    
    # Ensure RGB
    pil_img = pil_img.convert('RGB')
    
    # Resize to max_size while maintaining aspect ratio
    w, h = pil_img.size
    max_dim = max(w, h)
    if max_dim > max_size:
        scale = max_size / float(max_dim)
        new_w = int(w * scale)
        new_h = int(h * scale)
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
    
    return pil_img


def compute_phash_from_image(pil_img: Image.Image) -> int:
    # Preprocess before hashing for better matching
    pil_img = preprocess_image_for_matching(pil_img)
    return int(str(imagehash.phash(pil_img)), 16)


def hamming_distance_int(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def kmeans_palette(pil_img: Image.Image, k: int = 5) -> List[Dict[str, Any]]:
    img = pil_img.convert('RGB').resize((200, 200))
    arr = np.asarray(img).reshape(-1, 3).astype(np.float32)
    # Subsample for speed if huge
    if arr.shape[0] > 50000:
        idx = np.random.choice(arr.shape[0], 50000, replace=False)
        arr_sample = arr[idx]
    else:
        arr_sample = arr

    km = KMeans(n_clusters=k, n_init=5, random_state=42)
    labels = km.fit_predict(arr_sample)
    centers = km.cluster_centers_.astype(np.int32)

    # Compute percentages on the sampled set
    counts = np.bincount(labels, minlength=k)
    total = int(counts.sum()) if counts.sum() > 0 else 1

    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        return '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])

    palette = []
    for i in range(k):
        color = tuple(int(c) for c in centers[i])
        palette.append({
            'hex': rgb_to_hex(color),
            'percent': int(round(100 * (counts[i] / total)))
        })
    # Normalize percentages to sum ~100
    diff = 100 - sum(p['percent'] for p in palette)
    if palette and diff != 0:
        palette[0]['percent'] = max(0, min(100, palette[0]['percent'] + diff))
    return palette


def texture_edge_density(pil_img: Image.Image) -> float:
    img_rgb = pil_img.convert('RGB')
    img_np = np.array(img_rgb)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, threshold1=100, threshold2=200)
    edge_pixels = int(np.count_nonzero(edges))
    total_pixels = edges.size if edges.size > 0 else 1
    return edge_pixels / total_pixels


def decode_upload_to_image(req) -> Tuple[Image.Image, str]:
    # Returns (PIL.Image, error_message or '')
    if req.files and 'file' in req.files:
        f = req.files['file']
        try:
            img = Image.open(f.stream).convert('RGB')
            return img, ''
        except Exception as e:
            return None, f"Invalid image upload: {e}"
    else:
        try:
            data = req.get_json(silent=True) or {}
            b64data = data.get('image_base64')
            if not b64data:
                return None, 'No image provided. Expect multipart file "file" or JSON {"image_base64": dataURL}'
            if ',' in b64data:
                b64data = b64data.split(',', 1)[1]
            binary = base64.b64decode(b64data)
            img = Image.open(io.BytesIO(binary)).convert('RGB')
            return img, ''
        except Exception as e:
            return None, f"Invalid base64 image: {e}"


def ensure_analytics_log():
    if not os.path.exists(ANALYTICS_LOG):
        safe_write_json(ANALYTICS_LOG, [])


def load_embeddings() -> Dict[str, int]:
    if not os.path.exists(EMBEDDINGS_JSON):
        return {}
    with open(EMBEDDINGS_JSON, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    # Convert str->int
    res = {}
    for k, v in raw.items():
        try:
            res[k] = int(v)
        except Exception:
            continue
    return res


def save_embeddings(mapping: Dict[str, int]):
    # Store as strified ints
    out = {k: str(int(v)) for k, v in mapping.items()}
    safe_write_json(EMBEDDINGS_JSON, out)


@app.route('/')
def serve_index():
    # Serve frontend index.html
    index_path = os.path.join(FRONTEND_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return jsonify({"error": "frontend not found"}), 404


@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)


@app.route('/demo_mode_images/<path:filename>')
def serve_demo_images(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'demo_mode_images'), filename)


@app.route('/sw.js')
def serve_sw():
    return send_from_directory(FRONTEND_DIR, 'sw.js')


@app.route('/artworks.json')
def serve_artworks_json():
    if os.path.exists(ARTWORKS_JSON):
        return send_from_directory(BASE_DIR, 'artworks.json')
    return jsonify({}), 200


@app.route('/static/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'audio'), filename)


@app.route('/static/video/<path:filename>')
def serve_video(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'video'), filename)


@app.route('/images/<path:filename>')
def serve_image_files(filename):
    try:
        return send_from_directory(IMAGES_DIR, filename)
    except Exception:
        return jsonify({"error": "image not found"}), 404


@app.route('/precompute', methods=['POST'])
def precompute():
    if not ARTWORKS:
        return jsonify({"status": "error", "message": "artworks.json missing or empty"}), 400
    embeddings: Dict[str, int] = {}
    count = 0
    for art_id, meta in ARTWORKS.items():
        filename = meta.get('image')
        if not filename:
            continue
        path = os.path.join(IMAGES_DIR, filename)
        if not os.path.exists(path):
            continue
        try:
            with Image.open(path) as img:
                img = img.convert('RGB')
                ph = compute_phash_from_image(img)
                embeddings[art_id] = ph
                count += 1
        except Exception:
            continue
    save_embeddings(embeddings)
    return jsonify({"status": "ok", "count": count})


@app.route('/analyze', methods=['POST'])
def analyze():
    pil_img, err = decode_upload_to_image(request)
    if pil_img is None:
        return jsonify({"error": err}), 400

    # Compute features
    try:
        ph = compute_phash_from_image(pil_img)
    except Exception as e:
        return jsonify({"error": f"Failed to compute pHash: {e}"}), 500

    palette = []
    tex_density = 0.0
    try:
        palette = kmeans_palette(pil_img, k=5)
    except Exception:
        palette = []
    try:
        tex_density = texture_edge_density(pil_img)
    except Exception:
        tex_density = 0.0

    embeddings = load_embeddings()
    if not embeddings:
        return jsonify({"error": "No embeddings found. Run /precompute first."}), 400
    
    # Find best match
    best_id = None
    best_dist = None
    all_distances = []
    for art_id, emb in embeddings.items():
        d = hamming_distance_int(ph, emb)
        all_distances.append({"id": art_id, "distance": d})
        if best_dist is None or d < best_dist:
            best_dist = d
            best_id = art_id

    # Sort for debug
    all_distances.sort(key=lambda x: x["distance"])
    
    # More lenient threshold: allow up to 40 Hamming distance (was 32)
    # This accounts for camera variations, lighting, angle differences
    MAX_DISTANCE = 40
    confidence = max(0.0, min(1.0, 1.0 - (best_dist / 64.0)))
    matched = best_dist <= MAX_DISTANCE
    
    # Debug logging
    print(f"[ANALYZE] Best match: {best_id} (distance={best_dist}, confidence={confidence:.2f}, matched={matched})")
    print(f"[ANALYZE] Top 3 distances: {all_distances[:3]}")
    
    metadata = ARTWORKS.get(best_id) if matched else None

    resp = {
        "matched": bool(matched),
        "match_id": best_id if matched else None,
        "match_confidence": round(float(confidence), 4) if matched else None,
        "hamming_distance": int(best_dist),
        "palette": palette,
        "texture_edge_density": round(float(tex_density), 6),
        "debug": {
            "best_match": best_id,
            "best_distance": int(best_dist),
            "threshold": MAX_DISTANCE,
            "top_3": all_distances[:3]
        }
    }
    if metadata is not None:
        resp["metadata"] = metadata
    else:
        resp["message"] = f"No match found. Best distance was {best_dist} (threshold: {MAX_DISTANCE}). Try a clearer photo or ensure /precompute was run."
    return jsonify(resp)


@app.route('/artwork/<art_id>')
def artwork_meta(art_id: str):
    # Return JSON metadata (for API calls)
    meta = ARTWORKS.get(art_id)
    if not meta:
        return jsonify({"error": "not found"}), 404
    return jsonify(meta)


@app.route('/artwork-page/<art_id>')
def artwork_page(art_id: str):
    # Serve HTML page for artwork detail view
    artwork_html = os.path.join(FRONTEND_DIR, 'artwork.html')
    if os.path.exists(artwork_html):
        return send_from_directory(FRONTEND_DIR, 'artwork.html')
    return jsonify({"error": "artwork page not available"}), 404


@app.route('/analytics', methods=['POST'])
def analytics_single():
    ensure_analytics_log()
    event = request.get_json(silent=True) or {}
    # minimal validation
    event.setdefault('id', str(uuid.uuid4()))
    if 'timestamp' not in event:
        event['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    try:
        with open(ANALYTICS_LOG, 'r', encoding='utf-8') as f:
            arr = json.load(f)
    except Exception:
        arr = []
    arr.append(event)
    safe_write_json(ANALYTICS_LOG, arr)
    return jsonify({"status": "ok"})


@app.route('/sync-analytics', methods=['POST'])
def analytics_batch():
    ensure_analytics_log()
    payload = request.get_json(silent=True) or {}
    events = payload.get('events') or []
    # sanitize
    for e in events:
        e.setdefault('id', str(uuid.uuid4()))
        if 'timestamp' not in e:
            e['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    try:
        with open(ANALYTICS_LOG, 'r', encoding='utf-8') as f:
            arr = json.load(f)
    except Exception:
        arr = []
    arr.extend(events)
    safe_write_json(ANALYTICS_LOG, arr)
    return jsonify({"status": "ok", "received": len(events)})


# ==================== ADMIN ROUTES ====================

# Simple admin auth (for MVP - use env var in production)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
ADMIN_TOKENS = {}  # In-memory token store (use Redis in production)

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or token not in ADMIN_TOKENS:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
def serve_admin():
    admin_path = os.path.join(FRONTEND_DIR, 'admin.html')
    if os.path.exists(admin_path):
        return send_from_directory(FRONTEND_DIR, 'admin.html')
    return jsonify({"error": "admin page not found"}), 404

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    if password == ADMIN_PASSWORD:
        token = secrets.token_urlsafe(32)
        ADMIN_TOKENS[token] = datetime.utcnow()
        return jsonify({"token": token, "status": "ok"})
    return jsonify({"error": "Invalid password"}), 401

@app.route('/admin/artworks', methods=['GET'])
@require_admin
def admin_list_artworks():
    return jsonify({"artworks": ARTWORKS})

@app.route('/admin/artworks', methods=['POST'])
@require_admin
def admin_create_artwork():
    data = request.get_json(silent=True) or {}
    art_id = data.get('id')
    if not art_id:
        return jsonify({"error": "Artwork ID required"}), 400
    if art_id in ARTWORKS:
        return jsonify({"error": "Artwork ID already exists"}), 400
    
    artwork = {
        "id": art_id,
        "title": data.get('title', ''),
        "artist": data.get('artist', ''),
        "year": data.get('year', ''),
        "type": data.get('type'),
        "medium": data.get('medium'),
        "dimensions": data.get('dimensions'),
        "image": data.get('image', ''),
        "audio_url": data.get('audio_url'),
        "video_url": data.get('video_url'),
        "description_short": data.get('description_short'),
        "description_long": data.get('description_long'),
        "related": data.get('related', []),
        "tour_group": data.get('tour_group')
    }
    
    ARTWORKS[art_id] = artwork
    safe_write_json(ARTWORKS_JSON, ARTWORKS)
    return jsonify({"status": "ok", "artwork": artwork})

@app.route('/admin/artworks/<art_id>', methods=['GET'])
@require_admin
def admin_get_artwork(art_id: str):
    artwork = ARTWORKS.get(art_id)
    if not artwork:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"artwork": artwork})

@app.route('/admin/artworks/<art_id>', methods=['PUT'])
@require_admin
def admin_update_artwork(art_id: str):
    if art_id not in ARTWORKS:
        return jsonify({"error": "Not found"}), 404
    
    data = request.get_json(silent=True) or {}
    artwork = ARTWORKS[art_id]
    
    # Update fields
    for key in ['title', 'artist', 'year', 'type', 'medium', 'dimensions', 
                'image', 'audio_url', 'video_url', 'description_short', 
                'description_long', 'related', 'tour_group']:
        if key in data:
            artwork[key] = data[key]
    
    ARTWORKS[art_id] = artwork
    safe_write_json(ARTWORKS_JSON, ARTWORKS)
    return jsonify({"status": "ok", "artwork": artwork})

@app.route('/admin/artworks/<art_id>', methods=['DELETE'])
@require_admin
def admin_delete_artwork(art_id: str):
    if art_id not in ARTWORKS:
        return jsonify({"error": "Not found"}), 404
    
    del ARTWORKS[art_id]
    safe_write_json(ARTWORKS_JSON, ARTWORKS)
    return jsonify({"status": "ok"})

@app.route('/admin/artworks/<art_id>/image', methods=['POST'])
@require_admin
def admin_upload_image(art_id: str):
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Get filename from artwork or use provided
    artwork = ARTWORKS.get(art_id)
    if artwork:
        filename = artwork.get('image', f"{art_id}.jpg")
    else:
        filename = f"{art_id}.jpg"
    
    # Ensure filename has extension
    if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
        filename = f"{filename}.jpg"
    
    filepath = os.path.join(IMAGES_DIR, filename)
    file.save(filepath)
    
    # Update artwork image field if exists
    if artwork:
        artwork['image'] = filename
        ARTWORKS[art_id] = artwork
        safe_write_json(ARTWORKS_JSON, ARTWORKS)
    
    return jsonify({"status": "ok", "filename": filename})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode')
    args = parser.parse_args()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=bool(args.debug))


if __name__ == '__main__':
    main()