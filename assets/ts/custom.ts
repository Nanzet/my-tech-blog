// 显示语言和复制按钮
const highlights = document.querySelectorAll('.article-content div.highlight');

// ⚡️ 定义语言完美格式化字典 (语雀/大厂文档风格)
const langMap: { [key: string]: string } = {
    "python": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "html": "HTML",
    "css": "CSS",
    "scss": "SCSS",
    "json": "JSON",
    "yaml": "YAML",
    "yml": "YAML",
    "bash": "Bash",
    "shell": "Shell",
    "sh": "Shell",
    "go": "Go",
    "java": "Java",
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "rust": "Rust",
    "sql": "SQL",
    "php": "PHP",
    "ruby": "Ruby",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "markdown": "Markdown",
    "md": "Markdown",
    "xml": "XML",
    "vue": "Vue",
    "react": "React",
    "properties": "Properties",
    "ini": "INI"
};

highlights.forEach(highlight => {
    // 注释掉添加复制按钮的相关代码
    // const copyButton = document.createElement('button');
    // copyButton.innerHTML = copyText;
    // ...

    const codeBlock = highlight.querySelector('code[data-lang]');
    if (!codeBlock) return;

    // 获取原始语言标签
    const rawLang = codeBlock.getAttribute('data-lang');
    if (!rawLang) return;

    // 统一转小写用于字典匹配
    const lowerLang = rawLang.toLowerCase();

    // ⚡️ 核心替换逻辑：如果字典里有，就用字典里的完美拼写；如果没有，就做“首字母大写”处理
    const displayLang = langMap[lowerLang] || (lowerLang.charAt(0).toUpperCase() + lowerLang.slice(1));

    // Add language code button
    const languageButton = document.createElement('button');
    // 使用格式化后的 displayLang 替换原来的 lang.toUpperCase()
    languageButton.innerHTML = displayLang + '&nbsp;&nbsp;';
    languageButton.classList.add('languageCodeButton');

    highlight.appendChild(languageButton);
});

// 如果这里报错找不到 StackColorScheme，忽略它即可，或者是声明一下 declare class
new StackColorScheme(document.getElementById('dark-mode-toggle'));