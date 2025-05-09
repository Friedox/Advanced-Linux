#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/ioctl.h>
#include <linux/errno.h>
#include <linux/mutex.h>
#include <linux/usb.h>

#define DEVICE_NAME "int_stack"
#define CLASS_NAME "int_stack_class"

#define INT_STACK_MAGIC 'S'
#define INT_STACK_SET_SIZE _IOW(INT_STACK_MAGIC, 1, unsigned int)

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Student");
MODULE_DESCRIPTION("Integer Stack Kernel Module with USB Key");
MODULE_VERSION("1.0");

#define USB_VENDOR_ID  0x13fe  // Kingston
#define USB_PRODUCT_ID 0x4300  // USB DISK 2.0

static int major_number;
static struct class *int_stack_class = NULL;
static struct device *int_stack_device = NULL;
static int device_created = 0;

struct int_stack {
    int *data;
    unsigned int size;
    unsigned int top;
    struct mutex lock;
};

static struct int_stack *stack = NULL;

static struct usb_device_id pen_table[] = {
    { USB_DEVICE(USB_VENDOR_ID, USB_PRODUCT_ID) },
    {}
};
MODULE_DEVICE_TABLE(usb, pen_table);

static int int_stack_open(struct inode *inode, struct file *file);
static int int_stack_release(struct inode *inode, struct file *file);
static ssize_t int_stack_read(struct file *file, char __user *buf, size_t count, loff_t *offset);
static ssize_t int_stack_write(struct file *file, const char __user *buf, size_t count, loff_t *offset);
static long int_stack_ioctl(struct file *file, unsigned int cmd, unsigned long arg);
static int pen_probe(struct usb_interface *interface, const struct usb_device_id *id);
static void pen_disconnect(struct usb_interface *interface);

static struct file_operations fops = {
    .open = int_stack_open,
    .release = int_stack_release,
    .read = int_stack_read,
    .write = int_stack_write,
    .unlocked_ioctl = int_stack_ioctl,
    .owner = THIS_MODULE,
};

static struct usb_driver pen_driver = {
    .name = "electronic_key",
    .id_table = pen_table,
    .probe = pen_probe,
    .disconnect = pen_disconnect,
};

static int pen_probe(struct usb_interface *interface, const struct usb_device_id *id)
{
    printk(KERN_INFO "USB Key (%04X:%04X) plugged\n", id->idVendor, id->idProduct);
    
    if (!device_created) {
        int_stack_class = class_create(CLASS_NAME);
        if (IS_ERR(int_stack_class)) {
            printk(KERN_ALERT "Failed to register device class\n");
            return PTR_ERR(int_stack_class);
        }
        
        int_stack_device = device_create(int_stack_class, NULL, MKDEV(major_number, 0), NULL, DEVICE_NAME);
        if (IS_ERR(int_stack_device)) {
            class_destroy(int_stack_class);
            printk(KERN_ALERT "Failed to create the device\n");
            return PTR_ERR(int_stack_device);
        }
        
        device_created = 1;
        printk(KERN_INFO "Int Stack: device has been registered\n");
    }
    
    return 0;
}

static void pen_disconnect(struct usb_interface *interface)
{
    printk(KERN_INFO "USB Key removed\n");
    
    if (device_created) {
        device_destroy(int_stack_class, MKDEV(major_number, 0));
        class_unregister(int_stack_class);
        class_destroy(int_stack_class);
        device_created = 0;
        printk(KERN_INFO "Int Stack: device has been unregistered\n");
    }
}

static int initialize_stack(unsigned int size)
{
    if (stack) {
        if (stack->data) {
            kfree(stack->data);
        }
        stack->data = kmalloc(size * sizeof(int), GFP_KERNEL);
        if (!stack->data) {
            return -ENOMEM;
        }
        stack->size = size;
        stack->top = 0;
        return 0;
    }
    return -EINVAL;
}

static int int_stack_open(struct inode *inode, struct file *file)
{
    if (!stack) {
        stack = kmalloc(sizeof(struct int_stack), GFP_KERNEL);
        if (!stack) {
            return -ENOMEM;
        }
        
        stack->data = kmalloc(10 * sizeof(int), GFP_KERNEL);
        if (!stack->data) {
            kfree(stack);
            stack = NULL;
            return -ENOMEM;
        }
        
        stack->size = 10;
        stack->top = 0;
        mutex_init(&stack->lock);
    }
    
    return 0;
}

static int int_stack_release(struct inode *inode, struct file *file)
{
    return 0;
}

static ssize_t int_stack_read(struct file *file, char __user *buf, size_t count, loff_t *offset)
{
    int value = 0;
    int ret;
    
    if (!stack) {
        return -EINVAL;
    }
    
    if (mutex_lock_interruptible(&stack->lock)) {
        return -ERESTARTSYS;
    }
    
    if (stack->top == 0) {
        mutex_unlock(&stack->lock);
        return 0;
    }
    
    stack->top--;
    value = stack->data[stack->top];
    
    mutex_unlock(&stack->lock);
    
    ret = copy_to_user(buf, &value, sizeof(int));
    if (ret) {
        return -EFAULT;
    }
    
    return sizeof(int);
}

static ssize_t int_stack_write(struct file *file, const char __user *buf, size_t count, loff_t *offset)
{
    int value = 0;
    int ret;
    
    if (!stack) {
        return -EINVAL;
    }
    
    ret = copy_from_user(&value, buf, sizeof(int));
    if (ret) {
        return -EFAULT;
    }
    
    if (mutex_lock_interruptible(&stack->lock)) {
        return -ERESTARTSYS;
    }
    
    if (stack->top >= stack->size) {
        mutex_unlock(&stack->lock);
        return -ERANGE;
    }
    
    stack->data[stack->top] = value;
    stack->top++;
    
    mutex_unlock(&stack->lock);
    
    return sizeof(int);
}

static long int_stack_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    unsigned int new_size;
    int *new_data;
    int ret, i;
    
    if (!stack) {
        return -EINVAL;
    }
    
    switch (cmd) {
    case INT_STACK_SET_SIZE:
        ret = copy_from_user(&new_size, (unsigned int *)arg, sizeof(unsigned int));
        if (ret) {
            return -EFAULT;
        }
        
        if (new_size <= 0) {
            return -EINVAL;
        }
        
        if (mutex_lock_interruptible(&stack->lock)) {
            return -ERESTARTSYS;
        }
        
        new_data = kmalloc(new_size * sizeof(int), GFP_KERNEL);
        if (!new_data) {
            mutex_unlock(&stack->lock);
            return -ENOMEM;
        }
        
        for (i = 0; i < min(stack->top, new_size); i++) {
            new_data[i] = stack->data[i];
        }
        
        kfree(stack->data);
        stack->data = new_data;
        
        if (stack->top > new_size) {
            stack->top = new_size;
        }
        
        stack->size = new_size;
        
        mutex_unlock(&stack->lock);
        break;
        
    default:
        return -ENOTTY;
    }
    
    return 0;
}

static int __init int_stack_init(void)
{
    int result;
    
    major_number = register_chrdev(0, DEVICE_NAME, &fops);
    if (major_number < 0) {
        printk(KERN_ALERT "Int Stack failed to register a major number\n");
        return major_number;
    }
    
    device_created = 0;
    
    result = usb_register(&pen_driver);
    if (result) {
        unregister_chrdev(major_number, DEVICE_NAME);
        printk(KERN_ALERT "Failed to register USB driver: %d\n", result);
        return result;
    }
    
    printk(KERN_INFO "Int Stack: Registered USB driver\n");
    return 0;
}

static void __exit int_stack_exit(void)
{
    if (stack) {
        if (stack->data) {
            kfree(stack->data);
        }
        kfree(stack);
    }
    
    usb_deregister(&pen_driver);
    
    if (device_created) {
        device_destroy(int_stack_class, MKDEV(major_number, 0));
        class_unregister(int_stack_class);
        class_destroy(int_stack_class);
    }
    
    unregister_chrdev(major_number, DEVICE_NAME);
    printk(KERN_INFO "Int Stack: module unloaded\n");
}

module_init(int_stack_init);
module_exit(int_stack_exit);
