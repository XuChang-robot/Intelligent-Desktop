// 参数修正对话框脚本

// 全局变量
let originalParams = {};
let currentSchema = {};

// 初始化函数
function initParameterFixDialog(message, schema) {
    // 保存参数信息
    currentSchema = schema;
    originalParams = parseSchema(schema);
    
    // 更新消息
    document.querySelector('.message').textContent = message;
    
    // 生成表单
    generateForm(originalParams);
    
    // 绑定事件
    bindEvents();
}

// 解析schema
function parseSchema(schema) {
    const params = {};
    
    if (typeof schema === 'object' && schema !== null) {
        if (schema.properties) {
            // OpenAPI风格
            for (const [paramName, paramInfo] of Object.entries(schema.properties)) {
                params[paramName] = {
                    type: paramInfo.type || 'string',
                    description: paramInfo.description || '',
                    default: paramInfo.default || '',
                    required: schema.required && schema.required.includes(paramName)
                };
            }
        } else {
            // 直接键值对
            for (const [paramName, paramValue] of Object.entries(schema)) {
                params[paramName] = {
                    type: 'string',
                    description: '',
                    default: paramValue,
                    required: true
                };
            }
        }
    }
    
    return params;
}

// 生成表单
function generateForm(params) {
    const form = document.getElementById('parameter-form');
    form.innerHTML = '';
    
    for (const [paramName, paramInfo] of Object.entries(params)) {
        const formGroup = document.createElement('div');
        formGroup.className = 'form-group';
        
        // 创建标签
        const label = document.createElement('label');
        label.textContent = paramName;
        
        if (paramInfo.required) {
            const requiredSpan = document.createElement('span');
            requiredSpan.className = 'required';
            requiredSpan.textContent = ' *';
            label.appendChild(requiredSpan);
        }
        
        if (paramInfo.description) {
            const descSpan = document.createElement('span');
            descSpan.className = 'description';
            descSpan.textContent = `(${paramInfo.description})`;
            label.appendChild(descSpan);
        }
        
        formGroup.appendChild(label);
        
        // 创建输入控件
        let input;
        if (paramInfo.type === 'boolean') {
            input = document.createElement('input');
            input.type = 'checkbox';
            input.name = paramName;
            input.checked = String(paramInfo.default).toLowerCase() === 'true';
        } else if (paramInfo.type === 'number' || paramInfo.type === 'integer') {
            input = document.createElement('input');
            input.type = 'number';
            input.name = paramName;
            input.value = paramInfo.default;
        } else {
            input = document.createElement('input');
            input.type = 'text';
            input.name = paramName;
            input.value = paramInfo.default;
        }
        
        formGroup.appendChild(input);
        form.appendChild(formGroup);
    }
}

// 绑定事件
function bindEvents() {
    // 确认按钮
    document.getElementById('confirm-btn').addEventListener('click', function() {
        const params = collectFormData();
        sendResponse({ action: 'accept', content: params });
    });
    
    // 重置按钮
    document.getElementById('reset-btn').addEventListener('click', function() {
        generateForm(originalParams);
    });
    
    // 取消按钮
    document.getElementById('cancel-btn').addEventListener('click', function() {
        sendResponse({ action: 'decline' });
    });
}

// 收集表单数据
function collectFormData() {
    const form = document.getElementById('parameter-form');
    const formData = {};
    
    const inputs = form.querySelectorAll('input');
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            formData[input.name] = input.checked;
        } else {
            formData[input.name] = input.value;
        }
    });
    
    return formData;
}

// 发送响应
function sendResponse(response) {
    // 通过QWebChannel与Python代码通信
    if (window.pyqt && typeof window.pyqt.sendResponse === 'function') {
        window.pyqt.sendResponse(JSON.stringify(response));
    } else {
        // 备用方案
        alert(JSON.stringify(response));
    }
}

// 导出函数
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initParameterFixDialog
    };
}