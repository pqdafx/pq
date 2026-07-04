import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math

# --- 核心配置 ---
BLOCK_SIZE = 64
TOTAL_BLOCKS = 256
SYS_RESERVED = 4

FREE = 0
EOF = -1
RESERVED = -2


class FileNode:

    def __init__(self, name, is_dir, start_block, size=0, parent=None):
        self.name = name
        self.is_dir = is_dir
        self.start_block = start_block
        self.size = size
        self.parent = parent
        self.children = []


class FATFileSystem:

    def __init__(self):
        self.fat = [FREE] * TOTAL_BLOCKS
        self.root = FileNode("Root", True, SYS_RESERVED - 1)
        self.format_disk()

    def format_disk(self):
        self.fat = [FREE] * TOTAL_BLOCKS
        for i in range(SYS_RESERVED):
            self.fat[i] = RESERVED
        self.root.children = []

    def allocate_blocks(self, num_blocks):
        if num_blocks == 0: return EOF
        free_blocks = [i for i, val in enumerate(self.fat) if val == FREE]
        if len(free_blocks) < num_blocks: return None

        allocated = free_blocks[:num_blocks]
        start_block = allocated[0]
        for i in range(num_blocks - 1):
            self.fat[allocated[i]] = allocated[i + 1]
        self.fat[allocated[-1]] = EOF
        return start_block

    def free_blocks(self, start_block):
        curr = start_block
        while curr != EOF and curr != FREE and curr != RESERVED:
            next_block = self.fat[curr]
            self.fat[curr] = FREE
            curr = next_block


class FATSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FAT 文件系统模拟器")
        self.root.geometry("1100x550")

        self.fs = FATFileSystem()
        self.current_dir = self.fs.root

        self.left_frame = tk.Frame(self.root, width=600)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.setup_ui()
        self.update_tree_view()
        self.update_disk_view()

    def get_current_path(self):
        """获取当前所在路径字符串"""
        path = []
        curr = self.current_dir
        while curr is not None:
            path.insert(0, curr.name)
            curr = curr.parent
        return "/" + "/".join(path[1:]) if len(path) > 1 else "/"

    def setup_ui(self):
        self.path_var = tk.StringVar()
        tk.Label(self.left_frame, textvariable=self.path_var, font=("Arial", 11, "bold"), fg="blue").pack(anchor=tk.W,
                                                                                                          pady=5)

        self.tree = ttk.Treeview(self.left_frame, columns=("Name", "Type", "Size", "Block", "FullPath"),
                                 show="headings")
        self.tree.heading("Name", text="文件名")
        self.tree.heading("Type", text="类型")
        self.tree.heading("Size", text="大小(B)")
        self.tree.heading("Block", text="起始块")
        self.tree.heading("FullPath", text="当前完整路径")

        self.tree.column("Name", width=120)
        self.tree.column("Type", width=50, anchor=tk.CENTER)
        self.tree.column("Size", width=60, anchor=tk.E)
        self.tree.column("Block", width=60, anchor=tk.CENTER)
        self.tree.column("FullPath", width=200)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_select_file)
        self.tree.bind("<Double-1>", self.on_double_click)

        btn_frame1 = tk.Frame(self.left_frame)
        btn_frame1.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame1, text="创建文件", command=self.create_file, bg="#e0f7fa").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame1, text="创建目录", command=self.create_dir, bg="#dcedc8").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame1, text="返回上级目录 (..)", command=self.go_up_dir, bg="#ffe082").pack(side=tk.LEFT, padx=2)

        btn_frame2 = tk.Frame(self.left_frame)
        btn_frame2.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame2, text="复制文件", command=self.copy_file, bg="#fff9c4").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame2, text="删除选中", command=self.delete_item, bg="#ffcdd2").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame2, text="格式化磁盘", command=self.format_disk, bg="#cfd8dc").pack(side=tk.LEFT, padx=2)

        tk.Label(self.right_frame, text="磁盘物理扇区 (16x16 = 256盘块)", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        self.canvas = tk.Canvas(self.right_frame, width=400, height=400, bg="white")
        self.canvas.pack(pady=10)
        self.rectangles = []

        cell_size = 24
        for i in range(TOTAL_BLOCKS):
            row = i // 16
            col = i % 16
            rect = self.canvas.create_rectangle(
                col * cell_size + 5, row * cell_size + 5,
                col * cell_size + 5 + cell_size, row * cell_size + 5 + cell_size,
                fill="white", outline="gray")
            self.rectangles.append(rect)

        legend_frame = tk.Frame(self.right_frame)
        legend_frame.pack(fill=tk.X)
        tk.Label(legend_frame, text="■ 预留", fg="gray").pack(side=tk.LEFT, padx=2)
        tk.Label(legend_frame, text="■ 空闲", fg="lightgreen").pack(side=tk.LEFT, padx=2)
        tk.Label(legend_frame, text="■ 占用", fg="salmon").pack(side=tk.LEFT, padx=2)
        tk.Label(legend_frame, text="■ 选中", fg="deepskyblue").pack(side=tk.LEFT, padx=2)

    def update_tree_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        current_path_str = self.get_current_path()
        self.path_var.set(f"当前所处位置: {current_path_str}")

        for node in self.current_dir.children:
            type_str = "<DIR>" if node.is_dir else "FILE"
            sep = "" if current_path_str == "/" else "/"
            full_path = f"{current_path_str}{sep}{node.name}"

            self.tree.insert("", tk.END, values=(node.name, type_str, node.size, node.start_block, full_path))

    def update_disk_view(self, selected_start_block=None):
        selected_chain = []
        if selected_start_block is not None and selected_start_block >= 0:
            curr = selected_start_block
            while curr != EOF and curr != FREE and curr != RESERVED:
                selected_chain.append(curr)
                curr = self.fs.fat[curr]

        for i in range(TOTAL_BLOCKS):
            color = "lightgreen"
            if self.fs.fat[i] == RESERVED:
                color = "gray"
            elif i in selected_chain:
                color = "deepskyblue"
            elif self.fs.fat[i] != FREE:
                color = "salmon"
            self.canvas.itemconfig(self.rectangles[i], fill=color)

    def on_select_file(self, event):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        start_block = int(item['values'][3])  # Block 是第4列 (索引3)
        self.update_disk_view(selected_start_block=start_block)

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        name = str(item['values'][0])  # Name 是第1列 (索引0)

        for node in self.current_dir.children:
            if node.name == name and node.is_dir:
                self.current_dir = node
                self.update_tree_view()
                self.update_disk_view()
                break

    def go_up_dir(self):
        if self.current_dir.parent is not None:
            self.current_dir = self.current_dir.parent
            self.update_tree_view()
            self.update_disk_view()

    def create_dir(self):
        name = simpledialog.askstring("新建目录", "请输入新的文件夹名:", parent=self.root)
        if not name: return
        if any(child.name == name for child in self.current_dir.children):
            messagebox.showerror("错误", "该目录下已存在同名项目！")
            return

        start_block = self.fs.allocate_blocks(1)
        if start_block is None:
            messagebox.showerror("空间不足", "磁盘已满！")
            return

        new_dir = FileNode(name, True, start_block, size=BLOCK_SIZE, parent=self.current_dir)
        self.current_dir.children.append(new_dir)

        self.current_dir = new_dir
        self.update_tree_view()
        self.update_disk_view()

    def create_file(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("创建新文件")
        dialog.geometry("300x160")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="文件名称:").place(x=20, y=20)
        name_entry = tk.Entry(dialog, width=20)
        name_entry.place(x=100, y=20)
        name_entry.focus()

        tk.Label(dialog, text="文件大小(B):").place(x=20, y=60)
        size_entry = tk.Entry(dialog, width=20)
        size_entry.place(x=100, y=60)

        result_data = {}

        def on_confirm():
            n = name_entry.get().strip()
            s = size_entry.get().strip()
            if not n:
                messagebox.showwarning("提示", "文件名不能为空", parent=dialog)
                return
            try:
                size = int(s)
                if size <= 0: raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "大小必须是正整数", parent=dialog)
                return

            result_data['name'] = n
            result_data['size'] = size
            dialog.destroy()

        tk.Button(dialog, text="确定创建", command=on_confirm, bg="#b3e5fc").place(x=110, y=110)

        self.root.wait_window(dialog)

        if not result_data: return

        name = result_data['name']
        size = result_data['size']

        if any(child.name == name for child in self.current_dir.children):
            messagebox.showerror("错误", "该目录下已存在同名文件！")
            return

        needed_blocks = math.ceil(size / BLOCK_SIZE)
        start_block = self.fs.allocate_blocks(needed_blocks)

        if start_block is None:
            messagebox.showerror("空间不足", "磁盘空闲块不足！")
            return

        new_file = FileNode(name, False, start_block, size, parent=self.current_dir)
        self.current_dir.children.append(new_file)
        self.update_tree_view()
        self.update_disk_view()

        current_path_str = self.get_current_path()
        sep = "" if current_path_str == "/" else "/"
        full_created_path = f"{current_path_str}{sep}{name}"
        messagebox.showinfo("创建成功",
                            f"文件已创建在: \n{full_created_path}\n\n总共分配了 {needed_blocks} 个物理盘块。")

    def delete_recursive(self, node):
        if node.is_dir:
            for child in node.children:
                self.delete_recursive(child)
        self.fs.free_blocks(node.start_block)

    def delete_item(self):
        selected = self.tree.selection()
        if not selected: return

        item = self.tree.item(selected[0])
        name = str(item['values'][0])

        for node in self.current_dir.children:
            if node.name == name:
                self.delete_recursive(node)
                self.current_dir.children.remove(node)
                self.update_tree_view()
                self.update_disk_view()
                return

    def copy_file(self):
        selected = self.tree.selection()
        if not selected: return

        item = self.tree.item(selected[0])
        name = str(item['values'][0])

        source_node = None
        for node in self.current_dir.children:
            if node.name == name:
                source_node = node
                break

        if source_node.is_dir: return

        new_name = simpledialog.askstring("复制", f"新文件名:", initialvalue=name + "_copy", parent=self.root)
        if not new_name: return
        if any(child.name == new_name for child in self.current_dir.children): return

        needed_blocks = math.ceil(source_node.size / BLOCK_SIZE)
        new_start_block = self.fs.allocate_blocks(needed_blocks)
        if new_start_block is None: return

        new_file = FileNode(new_name, False, new_start_block, source_node.size, parent=self.current_dir)
        self.current_dir.children.append(new_file)
        self.update_tree_view()
        self.update_disk_view()

    def format_disk(self):
        if messagebox.askyesno("警告", "将清空所有数据！确定继续吗？"):
            self.fs.format_disk()
            self.current_dir = self.fs.root
            self.update_tree_view()
            self.update_disk_view()


if __name__ == "__main__":
    root = tk.Tk()
    app = FATSimulatorApp(root)
    root.mainloop()