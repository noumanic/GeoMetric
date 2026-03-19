import os
import subprocess
import sys

def install_and_run():
    # Install specifically what was missing previously
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'rembg[cpu]', 'filetype', 'pooch', 'pymatting', 'scikit-image', 'pillow', '-q'])
    
    try:
        from rembg import remove
        from PIL import Image
        print("Processing with rembg...")
        
        # Disable pooling/multiprocessing which sometimes breaks on Windows CLI
        import os
        os.environ["OMP_NUM_THREADS"] = "1"
        
        input_path = r'asset\geo_metric_logo.png'
        out_path = r'asset\geo_metric_logo_transparent_v3.png'
        
        with open(input_path, 'rb') as i:
            with open(out_path, 'wb') as o:
                # We can use the simple byte interface bypassing PIL issues
                input_data = i.read()
                subject = remove(input_data)
                o.write(subject)
                
        print("Done processing!")
        
        # update HTML
        html_path = r'outputs\interactive\dashboards\geometric_dashboard.html'
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('geo_metric_logo_transparent.png', 'geo_metric_logo_transparent_v3.png')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        print("HTML updated.")
        
    except Exception as e:
        print("Failed:", e)

install_and_run()
