import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import pytesseract
import re
import os
import threading
import time
from datetime import datetime
import queue
import json

# تنظیم مسیر Tesseract (ویندوز)
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except:
    pass

class BatchProcessor:
    """پردازشگر دسته‌ای تصاویر"""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.results = []
        self.processing = False
        
    def process_image(self, image_path, config):
        """پردازش یک تصویر"""
        try:
            img = Image.open(image_path)
            
            # پیش‌پردازش
            if img.mode != 'L':
                img = img.convert('L')
            
            if config['enhance_contrast']:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
            
            if config['denoise']:
                img = img.filter(ImageFilter.MedianFilter(size=3))
            
            if config['binary']:
                img = img.point(lambda x: 0 if x < 180 else 255, '1')
            
            # استخراج متن
            custom_config = r'--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,!?@#$%^&*()_-+={{}}[]|\\:;"\'<>/ '
            text = pytesseract.image_to_string(img, config=custom_config)
            
            # پاکسازی و استخراج کدها
            cleaned_text = self.clean_text(text)
            codes = self.extract_codes(text)
            
            return {
                'filename': os.path.basename(image_path),
                'path': image_path,
                'raw_text': text,
                'cleaned_text': cleaned_text,
                'codes': codes,
                'code_count': len(codes),
                'word_count': len(cleaned_text.split()),
                'char_count': len(cleaned_text),
                'processing_time': time.time(),
                'success': True
            }
            
        except Exception as e:
            return {
                'filename': os.path.basename(image_path),
                'path': image_path,
                'error': str(e),
                'success': False
            }
    
    def clean_text(self, text):
        """پاکسازی متن"""
        # حذف کاراکترهای غیر انگلیسی و غیر عددی
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_lines = []
        
        for line in lines:
            # فقط کاراکترهای انگلیسی، اعداد و علائم نگارشی مجاز
            line = re.sub(r'[^\x00-\x7F]+', '', line)
            line = re.sub(r'\s+', ' ', line)
            if line.strip():
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def extract_codes(self, text):
        """استخراج کدهای مختلف از متن"""
        codes = []
        
        # الگوهای مختلف برای کدها
        patterns = [
            r'\b[A-Z0-9]{6,12}\b',  # کدهای ۶-۱۲ کاراکتری حروف و اعداد
            r'\b\d{4,10}\b',         # اعداد ۴-۱۰ رقمی
            r'\b[A-Z]{2,5}\d{3,8}\b',  # ترکیب حروف و اعداد
            r'\b[A-Z]{3,8}\b',       # حروف بزرگ
            r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # ایمیل
            r'\bhttps?://\S+\b',     # لینک‌ها
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # آی‌پی آدرس
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            codes.extend(matches)
        
        # حذف موارد تکراری
        unique_codes = []
        seen = set()
        for code in codes:
            if code not in seen:
                seen.add(code)
                unique_codes.append(code)
        
        return unique_codes

class ModernOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🖼️ استخراج‌کننده متن و کد از تصاویر")
        self.root.geometry("1200x800")
        
        # متغیرها
        self.image_paths = []
        self.current_results = []
        self.batch_processor = BatchProcessor()
        self.processing = False
        
        # تنظیم استایل
        self.setup_styles()
        
        # ایجاد رابط کاربری
        self.create_widgets()
        
    def setup_styles(self):
        """تنظیم استایل‌ها"""
        self.colors = {
            'primary': '#2563eb',
            'secondary': '#475569',
            'success': '#10b981',
            'danger': '#ef4444',
            'warning': '#f59e0b',
            'light': '#f8fafc',
            'dark': '#1e293b',
            'sidebar': '#1e293b',
            'card': '#ffffff'
        }
        
        self.fonts = {
            'title': ('Segoe UI', 18, 'bold'),
            'heading': ('Segoe UI', 12, 'bold'),
            'normal': ('Segoe UI', 10),
            'mono': ('Cascadia Code', 10),
            'code': ('Cascadia Code', 12, 'bold')
        }
    
    def create_widgets(self):
        """ایجاد رابط کاربری"""
        # فریم اصلی
        main_frame = tk.Frame(self.root, bg='#f1f5f9')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # نوار کناری
        self.create_sidebar(main_frame)
        
        # ناحیه اصلی
        self.create_main_area(main_frame)
        
        # نوار وضعیت
        self.create_status_bar()
    
    def create_sidebar(self, parent):
        """ایجاد نوار کناری"""
        sidebar = tk.Frame(parent, bg=self.colors['sidebar'], width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        # لوگو
        logo_frame = tk.Frame(sidebar, bg=self.colors['sidebar'], height=80)
        logo_frame.pack(fill=tk.X, pady=(20, 10))
        
        tk.Label(
            logo_frame,
            text="📷 OCR Pro",
            font=self.fonts['title'],
            bg=self.colors['sidebar'],
            fg='white'
        ).pack()
        
        tk.Label(
            logo_frame,
            text="استخراج متن و کد از تصاویر",
            font=('Segoe UI', 9),
            bg=self.colors['sidebar'],
            fg='#94a3b8'
        ).pack()
        
        # دکمه‌های اصلی
        button_frame = tk.Frame(sidebar, bg=self.colors['sidebar'])
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # انتخاب تصاویر
        tk.Button(
            button_frame,
            text="📁 انتخاب تصاویر",
            font=self.fonts['heading'],
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            command=self.select_images,
            height=2,
            width=20
        ).pack(fill=tk.X, pady=(0, 10))
        
        # شروع پردازش
        self.process_btn = tk.Button(
            button_frame,
            text="▶ شروع پردازش",
            font=self.fonts['heading'],
            bg=self.colors['success'],
            fg='white',
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            command=self.start_processing,
            height=2,
            width=20,
            state=tk.DISABLED
        )
        self.process_btn.pack(fill=tk.X, pady=(0, 10))
        
        # توقف پردازش
        self.stop_btn = tk.Button(
            button_frame,
            text="⏹ توقف",
            font=self.fonts['heading'],
            bg=self.colors['danger'],
            fg='white',
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            command=self.stop_processing,
            height=2,
            width=20,
            state=tk.DISABLED
        )
        self.stop_btn.pack(fill=tk.X, pady=(0, 10))
        
        # تنظیمات
        tk.Label(
            sidebar,
            text="تنظیمات پردازش:",
            font=self.fonts['normal'],
            bg=self.colors['sidebar'],
            fg='#94a3b8',
            anchor='w'
        ).pack(fill=tk.X, padx=20, pady=(20, 5))
        
        settings_frame = tk.Frame(sidebar, bg=self.colors['sidebar'])
        settings_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # گزینه‌های پیش‌پردازش
        self.enhance_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_frame,
            text="بهبود کنتراست",
            variable=self.enhance_var,
            font=self.fonts['normal'],
            bg=self.colors['sidebar'],
            fg='white',
            selectcolor=self.colors['primary'],
            activebackground=self.colors['sidebar'],
            activeforeground='white'
        ).pack(anchor=tk.W)
        
        self.denoise_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_frame,
            text="حذف نویز",
            variable=self.denoise_var,
            font=self.fonts['normal'],
            bg=self.colors['sidebar'],
            fg='white',
            selectcolor=self.colors['primary'],
            activebackground=self.colors['sidebar'],
            activeforeground='white'
        ).pack(anchor=tk.W)
        
        self.binary_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_frame,
            text="باینری کردن",
            variable=self.binary_var,
            font=self.fonts['normal'],
            bg=self.colors['sidebar'],
            fg='white',
            selectcolor=self.colors['primary'],
            activebackground=self.colors['sidebar'],
            activeforeground='white'
        ).pack(anchor=tk.W)
        
        # استخراج کدهای خاص
        self.extract_codes_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_frame,
            text="استخراج کدها",
            variable=self.extract_codes_var,
            font=self.fonts['normal'],
            bg=self.colors['sidebar'],
            fg='white',
            selectcolor=self.colors['primary'],
            activebackground=self.colors['sidebar'],
            activeforeground='white'
        ).pack(anchor=tk.W)
        
        # آمار
        tk.Label(
            sidebar,
            text="📊 آمار:",
            font=self.fonts['normal'],
            bg=self.colors['sidebar'],
            fg='#94a3b8',
            anchor='w'
        ).pack(fill=tk.X, padx=20, pady=(20, 5))
        
        stats_frame = tk.Frame(sidebar, bg=self.colors['sidebar'])
        stats_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.stats_label = tk.Label(
            stats_frame,
            text="تصاویر: ۰\nکدها: ۰\nمتن: ۰ کلمه",
            font=self.fonts['normal'],
            bg=self.colors['sidebar'],
            fg='white',
            justify=tk.LEFT
        )
        self.stats_label.pack(anchor=tk.W)
    
    def create_main_area(self, parent):
        """ایجاد ناحیه اصلی"""
        main_area = tk.Frame(parent, bg='#f1f5f9')
        main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # هدر
        header = tk.Frame(main_area, bg='white', relief=tk.FLAT, bd=1)
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header,
            text="تصاویر انتخاب شده",
            font=self.fonts['heading'],
            bg='white',
            fg=self.colors['dark']
        ).pack(side=tk.LEFT, padx=20, pady=10)
        
        # دکمه‌های هدر
        header_buttons = tk.Frame(header, bg='white')
        header_buttons.pack(side=tk.RIGHT, padx=20)
        
        tk.Button(
            header_buttons,
            text="🗑️ پاک کردن همه",
            font=self.fonts['normal'],
            bg=self.colors['danger'],
            fg='white',
            relief=tk.FLAT,
            command=self.clear_all_images
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            header_buttons,
            text="📋 کپی همه",
            font=self.fonts['normal'],
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT,
            command=self.copy_all_results
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            header_buttons,
            text="💾 ذخیره همه",
            font=self.fonts['normal'],
            bg=self.colors['success'],
            fg='white',
            relief=tk.FLAT,
            command=self.save_all_results
        ).pack(side=tk.LEFT, padx=5)
        
        # قاب تصاویر با اسکرول
        images_frame = tk.Frame(main_area, bg='white', relief=tk.FLAT, bd=1)
        images_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # کانواس برای نمایش تصاویر
        self.canvas = tk.Canvas(images_frame, bg='white')
        scrollbar = ttk.Scrollbar(images_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='white')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # فریم نتایج
        results_frame = tk.LabelFrame(
            main_area,
            text="📋 نتایج استخراج",
            font=self.fonts['heading'],
            bg='white',
            fg=self.colors['dark'],
            relief=tk.FLAT,
            bd=1
        )
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # نوت‌بوک برای نمایش نتایج
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # تب متون استخراج شده
        self.text_tab = tk.Frame(self.notebook, bg='white')
        self.notebook.add(self.text_tab, text="متن‌ها")
        
        self.text_display = scrolledtext.ScrolledText(
            self.text_tab,
            font=self.fonts['mono'],
            bg='#f8fafc',
            fg='#334155',
            wrap=tk.WORD,
            height=10
        )
        self.text_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # تب کدهای استخراج شده
        self.codes_tab = tk.Frame(self.notebook, bg='white')
        self.notebook.add(self.codes_tab, text="کدها")
        
        self.codes_display = scrolledtext.ScrolledText(
            self.codes_tab,
            font=self.fonts['mono'],
            bg='#f8fafc',
            fg='#334155',
            wrap=tk.WORD,
            height=10
        )
        self.codes_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # نوار پیشرفت
        self.progress_frame = tk.Frame(main_area, bg='white', relief=tk.FLAT, bd=1)
        self.progress_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="آماده",
            font=self.fonts['normal'],
            bg='white',
            fg=self.colors['dark']
        )
        self.progress_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            length=300,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=20, pady=10)
    
    def create_status_bar(self):
        """ایجاد نوار وضعیت"""
        status_bar = tk.Frame(self.root, bg=self.colors['dark'], height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar.pack_propagate(False)
        
        self.status_text = tk.StringVar(value="آماده برای کار")
        tk.Label(
            status_bar,
            textvariable=self.status_text,
            font=self.fonts['normal'],
            bg=self.colors['dark'],
            fg='white'
        ).pack(side=tk.LEFT, padx=20)
        
        self.count_label = tk.Label(
            status_bar,
            text="تصاویر: ۰",
            font=self.fonts['normal'],
            bg=self.colors['dark'],
            fg='white'
        )
        self.count_label.pack(side=tk.RIGHT, padx=20)
    
    def select_images(self):
        """انتخاب چندین تصویر"""
        file_types = [
            ("تصاویر", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
            ("همه فایل‌ها", "*.*")
        ]
        
        filenames = filedialog.askopenfilenames(
            title="انتخاب تصاویر",
            filetypes=file_types
        )
        
        if filenames:
            # اضافه کردن تصاویر جدید
            for filename in filenames:
                if filename not in self.image_paths:
                    self.image_paths.append(filename)
            
            self.update_images_display()
            self.process_btn.config(state=tk.NORMAL)
            self.update_stats()
            self.status_text.set(f"{len(filenames)} تصویر انتخاب شد")
    
    def update_images_display(self):
        """به‌روزرسانی نمایش تصاویر"""
        # پاک کردن نمایش قبلی
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # نمایش تصاویر
        for i, image_path in enumerate(self.image_paths):
            self.add_image_card(image_path, i)
    
    def add_image_card(self, image_path, index):
        """اضافه کردن کارت تصویر"""
        card = tk.Frame(self.scrollable_frame, bg='white', relief=tk.GROOVE, bd=1)
        card.pack(fill=tk.X, padx=5, pady=5)
        
        # اطلاعات تصویر
        info_frame = tk.Frame(card, bg='white')
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # نام فایل
        filename_label = tk.Label(
            info_frame,
            text=os.path.basename(image_path),
            font=self.fonts['normal'],
            bg='white',
            fg=self.colors['dark'],
            anchor='w'
        )
        filename_label.pack(fill=tk.X)
        
        # مسیر
        path_label = tk.Label(
            info_frame,
            text=image_path[:50] + "..." if len(image_path) > 50 else image_path,
            font=('Segoe UI', 8),
            bg='white',
            fg='#64748b',
            anchor='w'
        )
        path_label.pack(fill=tk.X)
        
        # دکمه حذف
        delete_btn = tk.Button(
            card,
            text="❌",
            font=('Segoe UI', 10),
            bg='white',
            fg=self.colors['danger'],
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            command=lambda p=image_path: self.remove_image(p)
        )
        delete_btn.pack(side=tk.RIGHT, padx=10)
        
        # دکمه پیش‌نمایش
        preview_btn = tk.Button(
            card,
            text="👁️",
            font=('Segoe UI', 10),
            bg='white',
            fg=self.colors['primary'],
            relief=tk.FLAT,
            bd=0,
            cursor='hand2',
            command=lambda p=image_path: self.show_preview(p)
        )
        preview_btn.pack(side=tk.RIGHT, padx=5)
    
    def remove_image(self, image_path):
        """حذف یک تصویر"""
        if image_path in self.image_paths:
            self.image_paths.remove(image_path)
            self.update_images_display()
            self.update_stats()
            
            if not self.image_paths:
                self.process_btn.config(state=tk.DISABLED)
    
    def clear_all_images(self):
        """پاک کردن همه تصاویر"""
        if self.image_paths:
            if messagebox.askyesno("تأیید", "آیا از حذف تمام تصاویر مطمئن هستید؟"):
                self.image_paths.clear()
                self.update_images_display()
                self.process_btn.config(state=tk.DISABLED)
                self.update_stats()
                self.status_text.set("همه تصاویر پاک شدند")
    
    def show_preview(self, image_path):
        """نمایش پیش‌نمایش تصویر"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"پیش‌نمایش - {os.path.basename(image_path)}")
        preview_window.geometry("500x500")
        
        try:
            img = Image.open(image_path)
            img.thumbnail((450, 450))
            
            photo = ImageTk.PhotoImage(img)
            
            label = tk.Label(preview_window, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)
            
            info_label = tk.Label(
                preview_window,
                text=f"{os.path.basename(image_path)} - {img.size[0]}×{img.size[1]}",
                font=self.fonts['normal']
            )
            info_label.pack(pady=(0, 10))
            
        except Exception as e:
            tk.Label(
                preview_window,
                text=f"خطا در نمایش تصویر: {str(e)}",
                fg='red'
            ).pack(pady=20)
    
    def start_processing(self):
        """شروع پردازش تصاویر"""
        if not self.image_paths:
            return
        
        if self.processing:
            return
        
        self.processing = True
        self.current_results = []
        self.process_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # پاک کردن نتایج قبلی
        self.text_display.delete(1.0, tk.END)
        self.codes_display.delete(1.0, tk.END)
        
        # اجرای پردازش در thread جداگانه
        thread = threading.Thread(target=self.process_batch)
        thread.daemon = True
        thread.start()
    
    def process_batch(self):
        """پردازش دسته‌ای تصاویر"""
        total = len(self.image_paths)
        
        # تنظیمات پردازش
        config = {
            'enhance_contrast': self.enhance_var.get(),
            'denoise': self.denoise_var.get(),
            'binary': self.binary_var.get()
        }
        
        for i, image_path in enumerate(self.image_paths):
            if not self.processing:
                break
            
            # به‌روزرسانی پیشرفت
            progress = (i + 1) / total * 100
            self.root.after(0, self.update_progress, progress, f"پردازش {i+1} از {total}")
            
            # پردازش تصویر
            result = self.batch_processor.process_image(image_path, config)
            self.current_results.append(result)
            
            # نمایش نتایج
            self.root.after(0, self.display_result, result)
        
        # اتمام پردازش
        self.root.after(0, self.processing_complete)
    
    def update_progress(self, value, message):
        """به‌روزرسانی نوار پیشرفت"""
        self.progress_var.set(value)
        self.progress_label.config(text=message)
        self.status_text.set(message)
    
    def display_result(self, result):
        """نمایش نتیجه یک تصویر"""
        if result['success']:
            # نمایش متن
            self.text_display.insert(tk.END, f"\n{'='*50}\n")
            self.text_display.insert(tk.END, f"📄 {result['filename']}\n")
            self.text_display.insert(tk.END, f"{'='*50}\n")
            self.text_display.insert(tk.END, f"{result['cleaned_text']}\n")
            
            # نمایش کدها
            if self.extract_codes_var.get() and result['codes']:
                self.codes_display.insert(tk.END, f"\n📌 {result['filename']}\n")
                for code in result['codes']:
                    self.codes_display.insert(tk.END, f"  • {code}\n")
        else:
            self.text_display.insert(tk.END, f"\n❌ خطا در پردازش {result['filename']}: {result['error']}\n")
    
    def processing_complete(self):
        """اتمام پردازش"""
        self.processing = False
        self.process_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # محاسبه آمار
        total_codes = sum(r.get('code_count', 0) for r in self.current_results if r['success'])
        total_words = sum(r.get('word_count', 0) for r in self.current_results if r['success'])
        
        self.status_text.set(f"پردازش کامل شد - {len(self.current_results)} تصویر")
        
        messagebox.showinfo(
            "اتمام پردازش",
            f"✅ پردازش {len(self.current_results)} تصویر کامل شد!\n\n"
            f"• تعداد کل کدها: {total_codes}\n"
            f"• تعداد کل کلمات: {total_words}\n"
            f"• نتایج در تب‌های مربوطه نمایش داده شدند."
        )
        
        self.update_stats()
    
    def stop_processing(self):
        """توقف پردازش"""
        self.processing = False
        self.process_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_text.set("پردازش متوقف شد")
    
    def update_stats(self):
        """به‌روزرسانی آمار"""
        image_count = len(self.image_paths)
        self.count_label.config(text=f"تصاویر: {image_count}")
        
        if self.current_results:
            total_codes = sum(r.get('code_count', 0) for r in self.current_results if r['success'])
            total_words = sum(r.get('word_count', 0) for r in self.current_results if r['success'])
            
            stats_text = f"تصاویر: {image_count}\nکدها: {total_codes}\nمتن: {total_words} کلمه"
        else:
            stats_text = f"تصاویر: {image_count}\nکدها: ۰\nمتن: ۰ کلمه"
        
        self.stats_label.config(text=stats_text)
    
    def copy_all_results(self):
        """کپی تمام نتایج به کلیپ‌بورد"""
        if not self.current_results:
            messagebox.showwarning("هشدار", "نتیجه‌ای برای کپی کردن وجود ندارد")
            return
        
        all_text = ""
        
        for result in self.current_results:
            if result['success']:
                all_text += f"\n{'='*50}\n"
                all_text += f"📄 {result['filename']}\n"
                all_text += f"{'='*50}\n"
                all_text += f"{result['cleaned_text']}\n\n"
                
                if result['codes']:
                    all_text += "کدهای استخراج شده:\n"
                    for code in result['codes']:
                        all_text += f"  • {code}\n"
                    all_text += "\n"
        
        if all_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(all_text)
            self.status_text.set("تمام نتایج کپی شد")
            messagebox.showinfo("موفق", "تمامی نتایج به کلیپ‌بورد کپی شدند")
    
    def save_all_results(self):
        """ذخیره تمام نتایج در فایل"""
        if not self.current_results:
            messagebox.showwarning("هشدار", "نتیجه‌ای برای ذخیره وجود ندارد")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("فایل متنی", "*.txt"),
                ("فایل JSON", "*.json"),
                ("فایل CSV", "*.csv"),
                ("همه فایل‌ها", "*.*")
            ]
        )
        
        if filename:
            try:
                ext = os.path.splitext(filename)[1].lower()
                
                if ext == '.json':
                    self.save_as_json(filename)
                elif ext == '.csv':
                    self.save_as_csv(filename)
                else:
                    self.save_as_txt(filename)
                
                self.status_text.set(f"نتایج در {filename} ذخیره شد")
                messagebox.showinfo("موفق", f"نتایج در {filename} ذخیره شد")
                
            except Exception as e:
                messagebox.showerror("خطا", f"خطا در ذخیره فایل: {str(e)}")
    
    def save_as_txt(self, filename):
        """ذخیره به صورت TXT"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("نتایج استخراج متن و کد از تصاویر\n")
            f.write(f"تاریخ تولید: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"تعداد تصاویر: {len(self.current_results)}\n")
            f.write("="*60 + "\n\n")
            
            for result in self.current_results:
                if result['success']:
                    f.write(f"{'='*50}\n")
                    f.write(f"فایل: {result['filename']}\n")
                    f.write(f"{'='*50}\n\n")
                    
                    f.write("📝 متن استخراج شده:\n")
                    f.write(result['cleaned_text'])
                    f.write("\n\n")
                    
                    if result['codes']:
                        f.write("🔢 کدهای استخراج شده:\n")
                        for code in result['codes']:
                            f.write(f"  • {code}\n")
                        f.write("\n")
                    
                    f.write("📊 آمار:\n")
                    f.write(f"  • تعداد کلمات: {result['word_count']}\n")
                    f.write(f"  • تعداد کاراکترها: {result['char_count']}\n")
                    f.write(f"  • تعداد کدها: {result['code_count']}\n")
                    f.write("\n" + "="*60 + "\n\n")
    
    def save_as_json(self, filename):
        """ذخیره به صورت JSON"""
        output_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_images': len(self.current_results),
                'processed_images': sum(1 for r in self.current_results if r['success']),
                'total_codes': sum(r.get('code_count', 0) for r in self.current_results if r['success']),
                'total_words': sum(r.get('word_count', 0) for r in self.current_results if r['success'])
            },
            'results': self.current_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
    
    def save_as_csv(self, filename):
        """ذخیره به صورت CSV"""
        import csv
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            # هدر
            writer.writerow(['نام فایل', 'تعداد کلمات', 'تعداد کاراکترها', 'تعداد کدها', 'کدها', 'متن'])
            
            # داده‌ها
            for result in self.current_results:
                if result['success']:
                    codes_str = '; '.join(result['codes'])
                    text_preview = result['cleaned_text'][:100] + "..." if len(result['cleaned_text']) > 100 else result['cleaned_text']
                    
                    writer.writerow([
                        result['filename'],
                        result['word_count'],
                        result['char_count'],
                        result['code_count'],
                        codes_str,
                        text_preview
                    ])

def main():
    """تابع اصلی"""
    root = tk.Tk()
    
    # تنظیم آیکن
    try:
        root.iconbitmap("icon.ico")
    except:
        pass
    
    # ایجاد برنامه
    app = ModernOCRApp(root)
    
    # تنظیم حداقل اندازه
    root.minsize(1000, 700)
    
    # مرکز پنجره
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # شروع حلقه رویداد
    root.mainloop()

if __name__ == "__main__":
    main()
