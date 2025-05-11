from tkinter import *
from tkinter import colorchooser, ttk, filedialog, messagebox
from PIL import ImageGrab
import math

# 锚点类
class AnchorPoint:
    def __init__(self, x, y):
        # 坐标
        self.x = x
        self.y = y
        self.control_in = (x, y)  # 入控制点
        self.control_out = (x, y) # 出控制点
        self.locked = False       # 控制点锁定状态

class PenToolCanvas:
    def __init__(self, root):
        self.root = root
        # 画布
        self.canvas = Canvas(root, width=1000, height=700, bg='white')
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 控制面板
        self.control_frame = Frame(root)
        self.control_frame.pack(side=RIGHT, padx=10, pady=10)
        
        # 初始化参数
        self.line_width = 2
        self.line_color = "black"
        self.anchor_size = 5
        self.anchor_color = "red"
        self.handle_color = "blue"
        self.show_handles = BooleanVar(value=True)
        
        # 初始化组件，这些函数见下
        self.create_controls()
        self.init_data()
        self.bind_events()

    # 初始化数据
    def init_data(self):
        # 点的集合
        self.points = []
        # 选择的点的对象
        self.selected = None
        # 鼠标是否处于拖拽状态
        self.dragging = False
        # 历史记录，用于撤销操作
        self.history = []
        self.current_segment = None

    # 将键盘操作于函数绑定起来
    def bind_events(self):
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Key-Delete>", self.delete_selected)
        self.canvas.bind("<Control-z>", self.undo)
        self.canvas.focus_set()

    # 创建控制面板
    def create_controls(self):
        # 保存按钮
        Button(self.control_frame, text="保存为图片", 
              command=self.save_image).pack(pady=10)
        
        # 控制手柄可见性
        Checkbutton(self.control_frame, text="显示控制手柄", 
                   variable=self.show_handles,
                   command=self.redraw_canvas).pack(pady=5)
        
        # 线条样式设置
        Label(self.control_frame, text="线条粗细:").pack()
        Scale(self.control_frame, from_=1, to=10, orient=HORIZONTAL,
             command=lambda v: self.set_line_width(int(v))).pack()
        
        Button(self.control_frame, text="选择线条颜色", 
              command=self.choose_line_color).pack(pady=5)
        
        # 锚点样式设置
        Label(self.control_frame, text="锚点大小:").pack()
        Scale(self.control_frame, from_=3, to=10, orient=HORIZONTAL,
             command=lambda v: self.set_anchor_size(int(v))).pack()
        
        Button(self.control_frame, text="选择锚点颜色",
              command=self.choose_anchor_color).pack(pady=5)
        
        # 删除按钮
        Button(self.control_frame, text="删除选中元素", 
              command=self.delete_selected).pack(pady=10)

    #   鼠标释放事件处理
    def on_release(self, event):
        self.dragging = False
        self.push_history()

    # 添加新锚点
    def add_point(self, x, y):
        new_point = AnchorPoint(x, y)
        # 设置入控制点、出控制点
        if self.points:
            last_point = self.points[-1]
            last_point.control_out = (x, y)
            new_point.control_in = (x, y)
        self.points.append(new_point)
        # 重新渲染画布
        self.redraw_canvas()

    # 删除选中元素
    def delete_selected(self, event=None):
        if self.selected:
            point, _ = self.selected
            index = self.points.index(point)
            # 处理前后连接点
            if index > 0:
                prev_point = self.points[index-1]
                prev_point.control_out = (prev_point.x, prev_point.y)
            if index < len(self.points)-1:
                next_point = self.points[index+1]
                next_point.control_in = (next_point.x, next_point.y)
            self.points.remove(point)
            self.selected = None
            # 重新渲染，并保存历史
            self.redraw_canvas()
            self.push_history()

    # 保存为图片
    def save_image(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG文件", "*.png"), ("JPEG文件", "*.jpg"), ("所有文件", "*.*")]
        )
        if file_path:
            # 获取画布区域坐标
            x = self.root.winfo_rootx() + self.canvas.winfo_x()
            y = self.root.winfo_rooty() + self.canvas.winfo_y()
            x1 = x + self.canvas.winfo_width()
            y1 = y + self.canvas.winfo_height()
            
            # 截图并保存
            ImageGrab.grab(bbox=(x, y, x1, y1)).save(file_path)
            messagebox.showinfo("保存成功", f"图片已保存至：{file_path}")

    # 查找最近的锚点或控制点
    def find_nearest_point(self, x, y, radius=8):
        # 先检查控制点
        for point in self.points:
            if self.distance((x,y), point.control_in) < radius:
                return (point, 'in')
            if self.distance((x,y), point.control_out) < radius:
                return (point, 'out')
        # 检查锚点
        for point in self.points:
            if self.distance((x,y), (point.x, point.y)) < radius:
                return (point, 'anchor')
        return None

    # 计算两点距离
    def distance(self, pos1, pos2):
        return ((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)**0.5

    # 保存操作历史
    def push_history(self):
        self.history.append([(p.x, p.y, p.control_in, p.control_out) for p in self.points])

    # 撤销操作
    def undo(self, event=None):
        if self.history:
            # 拿上一次的历史记录来重新渲染画布
            self.history.pop()
            if self.history:
                self.points = [self.create_point_from_data(data) for data in self.history[-1]]
                self.redraw_canvas()

    # 从历史数据创建锚点
    def create_point_from_data(self, data):
        p = AnchorPoint(data[0], data[1])
        p.control_in = data[2]
        p.control_out = data[3]
        return p

    # 重绘画布
    def redraw_canvas(self):
        self.canvas.delete("all")
        # 绘制所有曲线
        for i in range(1, len(self.points)):
            self.draw_bezier_curve(self.points[i-1], self.points[i])
        # 绘制所有锚点
        for point in self.points:
            self.draw_anchor_point(point)
            if self.show_handles.get():
                self.draw_control_handles(point)
        # 高亮选中元素
        if self.selected:
            self.highlight_selected()

    # 绘制锚点
    def draw_anchor_point(self, point):
        size = self.anchor_size
        self.canvas.create_oval(point.x-size, point.y-size,
                               point.x+size, point.y+size,
                               fill=self.anchor_color, outline='black')

    # 绘制控制手柄
    def draw_control_handles(self, point):
        if point.control_in != (point.x, point.y):
            cx, cy = point.control_in
            self.canvas.create_line(cx, cy, point.x, point.y,
                                    dash=(2,2), fill=self.handle_color)
            self.canvas.create_oval(cx-2, cy-2, cx+2, cy+2,
                                    fill=self.handle_color)
        if point.control_out != (point.x, point.y):
            cx, cy = point.control_out
            self.canvas.create_line(cx, cy, point.x, point.y,
                                    dash=(2,2), fill=self.handle_color)
            self.canvas.create_oval(cx-2, cy-2, cx+2, cy+2,
                                    fill=self.handle_color)

    # 绘制贝塞尔曲线
    def draw_bezier_curve(self, p1, p2):
        steps = 20
        path = []
        for t in range(steps + 1):
            t_norm = t / steps
            x = ( (1-t_norm)**3 * p1.x 
                + 3*(1-t_norm)**2 * t_norm * p1.control_out[0]
                + 3*(1-t_norm) * t_norm**2 * p2.control_in[0]
                + t_norm**3 * p2.x )
            y = ( (1-t_norm)**3 * p1.y 
                + 3*(1-t_norm)**2 * t_norm * p1.control_out[1]
                + 3*(1-t_norm) * t_norm**2 * p2.control_in[1]
                + t_norm**3 * p2.y )
            path.extend([x, y])
        self.canvas.create_line(path, fill=self.line_color,
                               width=self.line_width, smooth=True)

    # 高亮选中元素
    def highlight_selected(self):
        point, point_type = self.selected
        if point_type == 'anchor':
            self.canvas.create_oval(point.x-6, point.y-6,
                                   point.x+6, point.y+6,
                                   outline='gold', width=2)
        else:
            cx, cy = point.control_in if point_type == 'in' else point.control_out
            self.canvas.create_oval(cx-4, cy-4, cx+4, cy+4,
                                   outline='gold', width=2)

    # 样式设置方法 
    def set_line_width(self, width):
        self.line_width = width
        self.redraw_canvas()

    def choose_line_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.line_color = color
            self.redraw_canvas()

    def set_anchor_size(self, size):
        self.anchor_size = size
        self.redraw_canvas()

    def choose_anchor_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.anchor_color = color
            self.redraw_canvas()

    # 计算点到线段的距离
    def point_to_line_distance(self, point, line_p1, line_p2):
        x0, y0 = point
        x1, y1 = line_p1
        x2, y2 = line_p2
        
        # 线段长度为零时返回点到端点的距离
        if x1 == x2 and y1 == y2:
            return self.distance(point, (x1, y1))
            
        # 计算投影参数
        t = ((x0 - x1)*(x2 - x1) + (y0 - y1)*(y2 - y1)) / ((x2 - x1)**2 + (y2 - y1)**2)
        t = max(0, min(1, t))  # 限制在0-1之间
        
        # 计算投影点
        proj_x = x1 + t*(x2 - x1)
        proj_y = y1 + t*(y2 - y1)
        
        return self.distance((x0, y0), (proj_x, proj_y))

    # 计算贝塞尔曲线上的点
    def bezier_point(self, p1, p2, t):

        x = ( (1-t)**3 * p1.x 
            + 3*(1-t)**2*t * p1.control_out[0]
            + 3*(1-t)*t**2 * p2.control_in[0]
            + t**3 * p2.x )
        y = ( (1-t)**3 * p1.y 
            + 3*(1-t)**2*t * p1.control_out[1]
            + 3*(1-t)*t**2 * p2.control_in[1]
            + t**3 * p2.y )
        return (x, y)
        
    # 增强的点击事件处理
    def on_click(self, event):
        # 优先检测控制点和锚点
        found = self.find_nearest_point(event.x, event.y)
        if found:
            self.selected = found
            self.dragging = True
            return
            
        # 检测线段点击（精度提升）
        segment, t = self.find_nearest_segment(event.x, event.y)
        if segment:
            self.insert_point_on_segment(segment, event.x, event.y)
            self.push_history()
            return
            
        # 添加新锚点
        self.add_point(event.x, event.y)
        self.push_history()
        
    # 改进的线段检测算法
    def find_nearest_segment(self, x, y, threshold=15):
        min_dist = float('inf')
        best_segment = None
        best_t = 0
        
        for i in range(len(self.points)-1):
            p1 = self.points[i]
            p2 = self.points[i+1]
            
            # 使用二分法查找最近点
            t, dist = self.find_closest_t(p1, p2, x, y)
            if dist < threshold and dist < min_dist:
                min_dist = dist
                best_segment = (i, i+1)
                best_t = t
                
        return best_segment, best_t

    # 精确查找最近点参数t（使用牛顿迭代法）
    def find_closest_t(self, p1, p2, x, y, iterations=10):
        # 初始猜测
        t = 0.5
        for _ in range(iterations):
            bx, by = self.bezier_point(p1, p2, t)
            dx = bx - x
            dy = by - y
            dist = dx*dx + dy*dy
            
            # 计算导数
            bx1, by1 = self.bezier_derivative(p1, p2, t)
            bx2, by2 = self.bezier_second_derivative(p1, p2, t)
            
            # 牛顿法迭代
            numerator = dx*bx1 + dy*by1
            denominator = (bx1**2 + by1**2) + (dx*bx2 + dy*by2)
            if denominator == 0:
                break
            t -= numerator / denominator
            t = max(0, min(1, t))
            
        # 计算最终距离
        bx, by = self.bezier_point(p1, p2, t)
        final_dist = math.hypot(bx-x, by-y)
        return t, final_dist

    # 贝塞尔曲线一阶导数
    def bezier_derivative(self, p1, p2, t):
        dx = 3*(1-t)**2*(p1.control_out[0]-p1.x) + \
             6*(1-t)*t*(p2.control_in[0]-p1.control_out[0]) + \
             3*t**2*(p2.x-p2.control_in[0])
             
        dy = 3*(1-t)**2*(p1.control_out[1]-p1.y) + \
             6*(1-t)*t*(p2.control_in[1]-p1.control_out[1]) + \
             3*t**2*(p2.y-p2.control_in[1])
             
        return (dx, dy)

    # 贝塞尔曲线二阶导数
    def bezier_second_derivative(self, p1, p2, t):
        ddx = 6*(1-t)*(p2.control_in[0]-2*p1.control_out[0]+p1.x) + \
              6*t*(p2.x-2*p2.control_in[0]+p1.control_out[0])
              
        ddy = 6*(1-t)*(p2.control_in[1]-2*p1.control_out[1]+p1.y) + \
              6*t*(p2.y-2*p2.control_in[1]+p1.control_out[1])
              
        return (ddx, ddy)

    # 改进的插入点算法
    def insert_point_on_segment(self, segment, x, y):
        idx1, idx2 = segment
        p1 = self.points[idx1]
        p2 = self.points[idx2]
        
        # 使用精确算法找到t值
        t, _ = self.find_closest_t(p1, p2, x, y)
        
        # 分割贝塞尔曲线
        new_point = AnchorPoint(0, 0)
        new_point.x, new_point.y = self.bezier_point(p1, p2, t)
        
        # 计算新控制点（保持曲线形状）
        new_point.control_in = (
            (1-t)*p1.control_out[0] + t*p2.control_in[0],
            (1-t)*p1.control_out[1] + t*p2.control_in[1]
        )
        new_point.control_out = (
            (1-t)*p2.control_in[0] + t*p2.x,
            (1-t)*p2.control_in[1] + t*p2.y
        )
        
        # 调整原有控制点
        p1.control_out = (
            (1-t)*p1.x + t*p1.control_out[0],
            (1-t)*p1.y + t*p1.control_out[1]
        )
        p2.control_in = (
            (1-t)*new_point.control_in[0] + t*p2.control_in[0],
            (1-t)*new_point.control_in[1] + t*p2.control_in[1]
        )
        
        self.points.insert(idx2, new_point)
        self.selected = (new_point, 'anchor')
        self.redraw_canvas()

    # 改进的拖拽控制逻辑
    def on_drag(self, event):
        if self.dragging and self.selected:
            point, point_type = self.selected
            
            # 移动锚点时保持相对控制点位置
            if point_type == 'anchor':
                dx = event.x - point.x
                dy = event.y - point.y
                point.x = event.x
                point.y = event.y
                point.control_in = (
                    point.control_in[0] + dx,
                    point.control_in[1] + dy
                )
                point.control_out = (
                    point.control_out[0] + dx,
                    point.control_out[1] + dy
                )
            else:
                # 控制点移动
                if point_type == 'in':
                    point.control_in = (event.x, event.y)
                    if not point.locked:
                        # 保持曲线平滑
                        dx = event.x - point.x
                        dy = event.y - point.y
                        point.control_out = (
                            point.x - dx,
                            point.y - dy
                        )
                else:
                    point.control_out = (event.x, event.y)
                    if not point.locked:
                        dx = event.x - point.x
                        dy = event.y - point.y
                        point.control_in = (
                            point.x - dx,
                            point.y - dy
                        )
            
            # 实时更新相邻曲线
            self.update_neighbor_curves(point)
            self.redraw_canvas()

    # 更新相邻曲线段的控制点
    def update_neighbor_curves(self, current_point):
        
        index = self.points.index(current_point)
        
        # 更新前一段曲线
        if index > 0:
            prev_point = self.points[index-1]
            prev_point.control_out = (
                current_point.control_in[0] + (current_point.x - prev_point.x)*0.3,
                current_point.control_in[1] + (current_point.y - prev_point.y)*0.3
            )
        
        # 更新后一段曲线
        if index < len(self.points)-1:
            next_point = self.points[index+1]
            next_point.control_in = (
                current_point.control_out[0] + (next_point.x - current_point.x)*0.3,
                current_point.control_out[1] + (next_point.y - current_point.y)*0.3
            )

if __name__ == "__main__":
    root = Tk()
    root.title("钢笔工具")
    app = PenToolCanvas(root)
    root.mainloop()
