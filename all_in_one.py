#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木模板开料机 G-code生成程序 - All-in-One 客户版
所有代码合并在一个文件中，专为PyInstaller打包设计
"""

import os
import sys
import json
import math
import time
import threading
import webbrowser
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import ezdxf
from ezdxf.math import Vec2

# ============= 资源路径处理 =============
def get_resource_path(relative_path):
    """获取资源文件路径（兼容PyInstaller打包）"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# ============= Flask应用初始化 =============
app = Flask(__name__, 
            template_folder=get_resource_path('templates'))

# 配置路径 - input和output目录在运行目录下，不在打包内
INPUT_PATH = os.path.join(os.getcwd(), "input")
OUTPUT_PATH = os.path.join(os.getcwd(), "output")

# 确保输入输出目录存在
os.makedirs(INPUT_PATH, exist_ok=True)
os.makedirs(OUTPUT_PATH, exist_ok=True)

# ============= 工具函数 =============
def safe_filename(filename):
    """安全文件名处理，支持中文但移除危险字符"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip('. ')
    if not filename or filename in ('.', '..'):
        filename = 'upload_file.dxf'
    return filename

# ============= DXF分析器 =============
class DXFAnalyzer:
    """DXF文件分析器"""
    
    def __init__(self):
        self.entities = []
        self.polylines = []
        self.circles = []
        self.texts = []
        
    def is_valid_coordinate(self, x, y, max_x=2500, max_y=3000):
        """检查坐标是否在合理范围内"""
        return 0 <= x <= max_x and 0 <= y <= max_y
    
    def filter_geometry(self, points):
        """过滤和修正几何坐标"""
        filtered_points = []
        for x, y in points:
            if self.is_valid_coordinate(x, y):
                filtered_points.append((x, y))
        return filtered_points
    
    def analyze_file(self, filepath):
        """分析DXF文件"""
        try:
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            self.entities = []
            self.polylines = []
            self.circles = []
            self.texts = []
            
            for entity in msp:
                entity_info = {
                    'type': entity.dxftype(),
                    'layer': entity.dxf.layer,
                    'entity': entity
                }
                
                if entity.dxftype() == 'LWPOLYLINE':
                    points = []
                    for point in entity.get_points():
                        x, y = point[0], point[1]
                        if self.is_valid_coordinate(x, y):
                            points.append((x, y))
                    
                    if len(points) >= 3:
                        entity_info['points'] = points
                        entity_info['closed'] = entity.closed
                        max_x = max(p[0] for p in points)
                        max_y = max(p[1] for p in points)
                        min_x = min(p[0] for p in points)
                        min_y = min(p[1] for p in points)
                        width = max_x - min_x
                        height = max_y - min_y
                        
                        if not (width > 1000 and height > 2000) and (width > 50 and height > 50) and len(self.polylines) < 2:
                            entity_info['area'] = width * height
                            self.polylines.append(entity_info)
                    
                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    if self.is_valid_coordinate(center.x, center.y) and 5 <= radius <= 50 and len(self.circles) < 4:
                        entity_info['center'] = (center.x, center.y)
                        entity_info['radius'] = radius
                        self.circles.append(entity_info)
                    
                elif entity.dxftype() == 'TEXT':
                    entity_info['text'] = entity.dxf.text
                    pos = entity.dxf.insert
                    if self.is_valid_coordinate(pos.x, pos.y):
                        entity_info['position'] = (pos.x, pos.y)
                        self.texts.append(entity_info)
                
                self.entities.append(entity_info)
                
            return {
                'success': True,
                'total_entities': len(self.entities),
                'polylines': len(self.polylines),
                'circles': len(self.circles),
                'texts': len(self.texts)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# ============= G代码生成器 =============
class GCodeGenerator:
    """G代码生成器"""
    
    def __init__(self):
        self.params = {
            'thickness': 18,
            'cutter_speed': 18000,
            'drill_speed': 18000,
            'feed_rate': 12000,
            'safe_height': 48,
            'cut_depth': 18,
            'drill_depth': 7,
            'process_order': 'drill_first'
        }
        
    def update_params(self, new_params):
        """更新加工参数"""
        self.params.update(new_params)
        
    def generate_header(self):
        """生成G代码文件头"""
        return ["G54"]
        
    def generate_tool_change(self, tool_num, spindle_speed):
        """生成换刀指令"""
        return [
            f"M6 T{tool_num}",
            f"M03 S{spindle_speed}",
            f"G43 H{tool_num}",
            f"G00 Z{self.params['safe_height']}.0"
        ]
        
    def generate_drill_hole(self, x, y, depth):
        """生成钻孔指令"""
        return [
            f"G00 X{x:.1f} Y{y:.1f}",
            f"G01 Z{depth:.1f} F3000",
            f"G00 Z{self.params['safe_height']}.0"
        ]
        
    def generate_cut_polyline(self, points, closed=True):
        """生成轮廓切割指令"""
        if not points or len(points) < 2:
            return []
            
        lines = []
        start_x, start_y = points[0]
        lines.append(f"G00 X{start_x:.1f} Y{start_y:.1f}")
        lines.append(f"G01 Z{self.params['cut_depth']:.1f} F3000")
        
        for i in range(1, len(points)):
            x, y = points[i]
            lines.append(f"G01 X{x:.1f} Y{y:.1f} F{self.params['feed_rate']}")
            
        if closed and len(points) > 2:
            lines.append(f"G01 X{start_x:.1f} Y{start_y:.1f}")
            
        lines.append(f"G00 Z{self.params['safe_height']}.0")
        return lines
        
    def generate_footer(self):
        """生成G代码文件尾"""
        return [
            "M05",
            "G53 X100.0Y2850.0",
            "M30",
        ]
        
    def generate_gcode(self, analyzer_data, filename_prefix="output"):
        """生成完整的G代码"""
        try:
            lines = []
            lines.extend(self.generate_header())
            
            if self.params['process_order'] == 'drill_first':
                if analyzer_data.circles:
                    lines.extend(self.generate_tool_change(2, self.params['drill_speed']))
                    for circle in analyzer_data.circles:
                        center_x, center_y = circle['center']
                        lines.extend(self.generate_drill_hole(center_x, center_y, self.params['drill_depth']))
                
                if analyzer_data.polylines:
                    lines.extend(self.generate_tool_change(1, self.params['cutter_speed']))
                    for polyline in analyzer_data.polylines:
                        lines.extend(self.generate_cut_polyline(polyline['points'], polyline['closed']))
            else:
                if analyzer_data.polylines:
                    lines.extend(self.generate_tool_change(1, self.params['cutter_speed']))
                    for polyline in analyzer_data.polylines:
                        lines.extend(self.generate_cut_polyline(polyline['points'], polyline['closed']))
                        
                if analyzer_data.circles:
                    lines.extend(self.generate_tool_change(2, self.params['drill_speed']))
                    for circle in analyzer_data.circles:
                        center_x, center_y = circle['center']
                        lines.extend(self.generate_drill_hole(center_x, center_y, self.params['drill_depth']))
            
            lines.extend(self.generate_footer())
            
            output_file = os.path.join(OUTPUT_PATH, f"{filename_prefix}.nc")
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + '\n')
                    
            return {
                'success': True,
                'filename': f"{filename_prefix}.nc",
                'lines_count': len(lines),
                'file_path': output_file
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# ============= Flask路由 =============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan_files')
def scan_files():
    """扫描输入目录中的DXF文件"""
    try:
        files = []
        if os.path.exists(INPUT_PATH):
            for filename in os.listdir(INPUT_PATH):
                if filename.lower().endswith('.dxf'):
                    filepath = os.path.join(INPUT_PATH, filename)
                    file_info = {
                        'name': filename,
                        'path': filepath,
                        'size': os.path.getsize(filepath),
                        'mtime': os.path.getmtime(filepath)
                    }
                    files.append(file_info)
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传DXF文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未找到文件'})
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': '未选择文件'})
        
        if not file.filename.lower().endswith('.dxf'):
            return jsonify({'success': False, 'error': '只支持DXF格式文件'})
        
        filename = safe_filename(file.filename)
        filepath = os.path.join(INPUT_PATH, filename)
        
        if os.path.exists(filepath):
            message = f'文件 {filename} 已存在，已替换为新版本'
        else:
            message = f'文件 {filename} 上传成功'
            
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': message
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    """删除文件API"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'success': False, 'error': '缺少文件名参数'})
        
        filename = data['filename']
        filepath = os.path.join(INPUT_PATH, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 删除成功'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/generate', methods=['POST'])
def generate_gcode_api():
    """生成G代码API"""
    try:
        dxf_analyzer = DXFAnalyzer()
        gcode_generator = GCodeGenerator()
        
        data = request.get_json()
        if data and 'params' in data:
            gcode_generator.update_params(data['params'])
        
        selected_files = data.get('selected_files', []) if data else []
        
        results = []
        
        if not os.path.exists(INPUT_PATH):
            return jsonify({
                'success': False,
                'error': '输入目录不存在，请先上传DXF文件'
            })
        
        if selected_files:
            dxf_files = [f for f in selected_files if f.lower().endswith('.dxf') and os.path.exists(os.path.join(INPUT_PATH, f))]
        else:
            dxf_files = [f for f in os.listdir(INPUT_PATH) if f.lower().endswith('.dxf')]
        
        if not dxf_files:
            return jsonify({
                'success': False,
                'error': '未找到要处理的DXF文件'
            })
            
        for dxf_file in dxf_files:
            filepath = os.path.join(INPUT_PATH, dxf_file)
            analysis_result = dxf_analyzer.analyze_file(filepath)
            
            if analysis_result['success']:
                filename_prefix = os.path.splitext(dxf_file)[0]
                gcode_result = gcode_generator.generate_gcode(dxf_analyzer, filename_prefix)
                
                result = {
                    'dxf_file': dxf_file,
                    'analysis': analysis_result,
                    'gcode': gcode_result
                }
                results.append(result)
            else:
                results.append({
                    'dxf_file': dxf_file,
                    'analysis': analysis_result,
                    'gcode': {'success': False, 'error': 'DXF分析失败'}
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total_files': len(results)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download/<filename>')
def download_file_api(filename):
    """下载生成的NC文件"""
    try:
        filepath = os.path.join(OUTPUT_PATH, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= 启动函数 =============
def check_port_available(port):
    """检查端口是否可用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except OSError:
        return False

def find_available_port(start_port=5001, max_attempts=10):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        if check_port_available(port):
            return port
    return None

def wait_for_server(port, timeout=10):
    """等待服务器启动"""
    import socket
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def open_browser_when_ready(url, port):
    """等待服务器就绪后打开浏览器"""
    print("等待服务器启动...")
    if wait_for_server(port, timeout=15):
        print(f"服务器已就绪，正在打开浏览器: {url}")
        time.sleep(1)
        try:
            webbrowser.open(url)
            print("浏览器已打开，如果没有自动跳转，请手动访问上述地址")
        except Exception as e:
            print(f"无法自动打开浏览器: {e}")
            print("请手动打开浏览器并访问上述地址")
    else:
        print("警告: 服务器启动超时，请检查命令行窗口的错误信息")

def main():
    """主函数"""
    print("=" * 60)
    print("木模板开料机 G-code生成程序")
    print("客户测试版 v1.0")
    print("=" * 60)
    
    # 检查input目录中的文件
    final_files = []
    try:
        final_files = [f for f in os.listdir(INPUT_PATH) if f.endswith('.dxf')]
    except:
        pass
    
    if final_files:
        print(f"\ninput目录中有 {len(final_files)} 个DXF文件可供测试")
    else:
        print("\ninput目录为空，请通过Web界面上传DXF文件")
    
    # 检查并选择可用端口
    print("\n正在检查端口...")
    port = find_available_port(5001, 10)
    
    if port is None:
        print("\n" + "=" * 60)
        print("错误: 无法找到可用端口（5001-5010都被占用）")
        print("=" * 60)
        print("\n请尝试以下解决方案:")
        print("1. 关闭其他可能占用端口的程序")
        print("2. 重启计算机后再试")
        print("3. 联系技术支持")
        input("\n按回车键退出...")
        return
    
    if port != 5001:
        print(f"注意: 端口5001被占用，已自动切换到端口{port}")
    
    url = f"http://localhost:{port}"
    
    print(f"\n正在启动Web服务器...")
    print("请稍候，系统启动需要几秒钟...")
    
    # 在后台线程中等待服务器就绪后打开浏览器
    browser_thread = threading.Thread(target=open_browser_when_ready, args=(url, port))
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        print("\n" + "=" * 60)
        print("系统正在启动中...")
        print(f"访问地址: {url}") 
        print("浏览器将在服务器就绪后自动打开...")
        print("\n重要提示：请不要关闭此命令行窗口！")
        print("         关闭此窗口将停止程序运行")
        print("=" * 60 + "\n")
        
        # 启动Flask服务器
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\n程序已停止")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n错误: 端口{port}被占用")
            print("请关闭占用该端口的程序后重试")
        else:
            print(f"\n程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        print("\n可能的解决方案:")
        print("1. 尝试以管理员身份运行")
        print("2. 检查防火墙设置")
        print("3. 检查杀毒软件是否阻止了程序")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

