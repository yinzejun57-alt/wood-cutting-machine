#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木模板开料机 G-code生成程序 - Demo版
作者: AI开发团队
版本: v1.0
日期: 2025-10-16
"""

import os
import sys
import json
import math
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import re
import ezdxf
from ezdxf.math import Vec2

app = Flask(__name__)

# 配置路径
INPUT_PATH = os.path.join(os.getcwd(), "input")  # 改为相对路径
OUTPUT_PATH = os.path.join(os.getcwd(), "output")

# 确保输入输出目录存在
os.makedirs(INPUT_PATH, exist_ok=True)
os.makedirs(OUTPUT_PATH, exist_ok=True)

def safe_filename(filename):
    """安全文件名处理，支持中文但移除危险字符"""
    # 移除路径分隔符和危险字符，但保留中文
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 移除开头和结尾的点和空格
    filename = filename.strip('. ')
    # 如果文件名为空或只包含点，使用默认名称
    if not filename or filename in ('.', '..'):
        filename = 'upload_file.dxf'
    return filename

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
                    # 解析轮廓线
                    points = []
                    for point in entity.get_points():
                        x, y = point[0], point[1]
                        if self.is_valid_coordinate(x, y):
                            points.append((x, y))
                    
                    # 只保留有效的轮廓线（至少3个点且形成合理形状）
                    if len(points) >= 3:
                        entity_info['points'] = points
                        entity_info['closed'] = entity.closed
                        # 过滤掉过大的轮廓（可能是板材边框）
                        max_x = max(p[0] for p in points)
                        max_y = max(p[1] for p in points)
                        min_x = min(p[0] for p in points)
                        min_y = min(p[1] for p in points)
                        width = max_x - min_x
                        height = max_y - min_y
                        
                        # 过滤掉板材边框（尺寸过大的矩形）和过小的零件，限制轮廓数量
                        if not (width > 1000 and height > 2000) and (width > 50 and height > 50) and len(self.polylines) < 2:
                            # 优先选择较大的零件
                            entity_info['area'] = width * height
                            self.polylines.append(entity_info)
                    
                elif entity.dxftype() == 'CIRCLE':
                    # 解析圆形 - 限制圆孔数量，只处理前4个
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    if self.is_valid_coordinate(center.x, center.y) and 5 <= radius <= 50 and len(self.circles) < 4:
                        entity_info['center'] = (center.x, center.y)
                        entity_info['radius'] = radius
                        self.circles.append(entity_info)
                    
                elif entity.dxftype() == 'TEXT':
                    # 解析文字
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

class GCodeGenerator:
    """G代码生成器"""
    
    def __init__(self):
        # 默认加工参数
        self.params = {
            'thickness': 18,           # 板材厚度
            'cutter_speed': 18000,     # 开料刀转速
            'drill_speed': 18000,      # 钻孔刀转速
            'feed_rate': 12000,        # 进给速度
            'safe_height': 48,         # 安全高度
            'cut_depth': 18,           # 切割深度
            'drill_depth': 7,          # 钻孔深度
            'process_order': 'drill_first'  # 加工顺序
        }
        
    def update_params(self, new_params):
        """更新加工参数"""
        self.params.update(new_params)
        
    def generate_header(self):
        """生成G代码文件头"""
        lines = [
            "G54",  # 工件坐标系
        ]
        return lines
        
    def generate_tool_change(self, tool_num, spindle_speed):
        """生成换刀指令"""
        lines = [
            f"M6 T{tool_num}",                    # 换刀
            f"M03 S{spindle_speed}",              # 启动主轴
            f"G43 H{tool_num}",                   # 刀具长度补偿
            f"G00 Z{self.params['safe_height']}.0"  # 抬到安全高度
        ]
        return lines
        
    def generate_drill_hole(self, x, y, depth):
        """生成钻孔指令"""
        lines = [
            f"G00 X{x:.1f} Y{y:.1f}",           # 定位到孔位
            f"G01 Z{depth:.1f} F3000",          # 下刀钻孔
            f"G00 Z{self.params['safe_height']}.0"  # 抬刀
        ]
        return lines
        
    def generate_cut_polyline(self, points, closed=True):
        """生成轮廓切割指令"""
        if not points or len(points) < 2:
            return []
            
        lines = []
        
        # 移动到起点
        start_x, start_y = points[0]
        lines.append(f"G00 X{start_x:.1f} Y{start_y:.1f}")
        lines.append(f"G01 Z{self.params['cut_depth']:.1f} F3000")
        
        # 切割路径
        for i in range(1, len(points)):
            x, y = points[i]
            lines.append(f"G01 X{x:.1f} Y{y:.1f} F{self.params['feed_rate']}")
            
        # 如果是封闭轮廓，回到起点
        if closed and len(points) > 2:
            lines.append(f"G01 X{start_x:.1f} Y{start_y:.1f}")
            
        # 抬刀
        lines.append(f"G00 Z{self.params['safe_height']}.0")
        
        return lines
        
    def generate_footer(self):
        """生成G代码文件尾"""
        lines = [
            "M05",                              # 停止主轴
            "G53 X100.0Y2850.0",               # 回到换刀点
            "M30",                             # 程序结束
        ]
        return lines
        
    def generate_gcode(self, analyzer_data, filename_prefix="output"):
        """生成完整的G代码"""
        try:
            lines = []
            
            # 文件头
            lines.extend(self.generate_header())
            
            if self.params['process_order'] == 'drill_first':
                # 先钻孔
                if analyzer_data.circles:
                    lines.extend(self.generate_tool_change(2, self.params['drill_speed']))
                    for circle in analyzer_data.circles:
                        center_x, center_y = circle['center']
                        lines.extend(self.generate_drill_hole(center_x, center_y, self.params['drill_depth']))
                
                # 后开料
                if analyzer_data.polylines:
                    lines.extend(self.generate_tool_change(1, self.params['cutter_speed']))
                    for polyline in analyzer_data.polylines:
                        lines.extend(self.generate_cut_polyline(polyline['points'], polyline['closed']))
            else:
                # 先开料
                if analyzer_data.polylines:
                    lines.extend(self.generate_tool_change(1, self.params['cutter_speed']))
                    for polyline in analyzer_data.polylines:
                        lines.extend(self.generate_cut_polyline(polyline['points'], polyline['closed']))
                        
                # 后钻孔
                if analyzer_data.circles:
                    lines.extend(self.generate_tool_change(2, self.params['drill_speed']))
                    for circle in analyzer_data.circles:
                        center_x, center_y = circle['center']
                        lines.extend(self.generate_drill_hole(center_x, center_y, self.params['drill_depth']))
            
            # 文件尾
            lines.extend(self.generate_footer())
            
            # 保存文件
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

# 全局对象
dxf_analyzer = DXFAnalyzer()
gcode_generator = GCodeGenerator()

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
            return jsonify({
                'success': False,
                'error': '未找到文件'
            })
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            })
        
        if not file.filename.lower().endswith('.dxf'):
            return jsonify({
                'success': False,
                'error': '只支持DXF格式文件'
            })
        
        # 保存文件
        filename = safe_filename(file.filename)
        filepath = os.path.join(INPUT_PATH, filename)
        
        # 检查文件是否已存在，如果存在则替换
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
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    """删除文件API"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '缺少文件名参数'
            })
        
        filename = data['filename']
        filepath = os.path.join(INPUT_PATH, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            })
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 删除成功'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/generate', methods=['POST'])
def generate_gcode():
    """生成G代码API"""
    try:
        # 创建处理器实例
        dxf_analyzer = DXFAnalyzer()
        gcode_generator = GCodeGenerator()
        
        # 获取请求参数
        data = request.get_json()
        if data and 'params' in data:
            gcode_generator.update_params(data['params'])
        
        # 获取选中的文件列表
        selected_files = data.get('selected_files', []) if data else []
        
        # 处理选中的DXF文件
        results = []
        
        if not os.path.exists(INPUT_PATH):
            return jsonify({
                'success': False,
                'error': '输入目录不存在，请先上传DXF文件'
            })
        
        # 如果有选中的文件，使用选中的文件；否则使用所有文件
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
            
            # 分析DXF文件
            analysis_result = dxf_analyzer.analyze_file(filepath)
            
            if analysis_result['success']:
                # 生成G代码
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
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/download/<filename>')
def download_file(filename):
    """下载生成的NC文件"""
    try:
        filepath = os.path.join(OUTPUT_PATH, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("木模板开料机 G-code生成程序 Demo启动中...")
    print(f"输入路径: {INPUT_PATH}")
    print(f"输出路径: {OUTPUT_PATH}")
    print("访问地址: http://localhost:5000")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
