// 显示语言和复制按钮
const highlights = document.querySelectorAll('.article-content div.highlight');

highlights.forEach(highlight => {
    // 注释掉添加复制按钮的相关代码
    // const copyButton = document.createElement('button');
    // copyButton.innerHTML = copyText;
    // copyButton.classList.add('copyCodeButton');
    // highlight.appendChild(copyButton);

    const codeBlock = highlight.querySelector('code[data-lang]');
    // 获取语言
    const lang = codeBlock.getAttribute('data-lang');
    if (!codeBlock) return;

    // copyButton.addEventListener('click', () => {
    //     navigator.clipboard.writeText(codeBlock.textContent)
    //         .then(() => {
    //             copyButton.textContent = copiedText;

    //             setTimeout(() => {
    //                 copyButton.textContent = copyText;
    //             }, 1000);
    //         })
    //         .catch(err => {
    //             alert(err)
    //             console.log('Something went wrong', err);
    //         });
    // });

    // Add language code button
    const languageButton = document.createElement('button');
    languageButton.innerHTML = lang.toUpperCase() + '&nbsp;&nbsp;';
    languageButton.classList.add('languageCodeButton');

    highlight.appendChild(languageButton);
});

new StackColorScheme(document.getElementById('dark-mode-toggle'));
