// static/admin/js/transaction_actions.js
// Полная система действий для транзакций с календарными кнопками

(function($) {
    $(document).ready(function() {
        
        console.log('🔥 Инициализация кнопок действий для транзакций...');
        
        // Ждем загрузки существующих скриптов
        setTimeout(function() {
            initializeTransactionActions();
        }, 1500);
        
        function initializeTransactionActions() {
            console.log('🔥 Активация системы действий...');
            
            // Добавляем обработчики для кнопок
            bindActionButtons();
            
            // Настраиваем readonly поля для существующих транзакций
            setupReadonlyFields();
            
            // Добавляем календарные кнопки
            setTimeout(function() {
                addCalendarButtons();
            }, 500);
        }
        
        function bindActionButtons() {
            // Снимаем предыдущие обработчики, чтобы избежать дублирования
            $(document).off('click.transactionActions');
            
            // Обработчик кнопки редактирования
            $(document).on('click.transactionActions', '.django-btn-edit', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const transactionId = $(this).data('id');
                const button = $(this);
                
                console.log('✏️ Клик на редактирование для ID:', transactionId);
                toggleEditMode(transactionId, button);
            });
            
            // Обработчик кнопки удаления
            $(document).on('click.transactionActions', '.django-btn-delete', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const transactionId = $(this).data('id');
                const button = $(this);
                
                console.log('🗑️ Клик на удаление для ID:', transactionId);
                softDeleteTransaction(transactionId, button);
            });
            
            // Обработчик кнопки восстановления
            $(document).on('click.transactionActions', '.django-btn-restore', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const button = $(this);
                const row = button.closest('tr');
                
                console.log('↶ Клик на восстановление');
                restoreTransaction(row, button);
            });
        }
        
        function toggleEditMode(transactionId, button) {
            // Показываем индикатор загрузки
            const originalContent = button.html();
            button.html('⏳').prop('disabled', true);
            
            // AJAX запрос к Django
            $.ajax({
                url: `/admin/investments/project/ajax/toggle-edit/${transactionId}/`,
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function(response) {
                    if (response.status === 'success') {
                        const row = button.closest('tr');
                        
                        if (response.mode === 'editable') {
                            // Переводим в режим редактирования
                            makeRowEditable(row);
                            button.html('💾').attr('title', 'Завершить редактирование');
                            showMessage(response.message, 'success');
                        } else {
                            // Переводим в режим только чтения
                            makeRowReadonly(row);
                            button.html('✏️').attr('title', 'Редактировать');
                            showMessage(response.message, 'info');
                        }
                    } else {
                        showMessage('Ошибка: ' + response.message, 'error');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX Error:', error);
                    showMessage('Ошибка сети: ' + error, 'error');
                },
                complete: function() {
                    button.prop('disabled', false);
                    if (button.html() === '⏳') {
                        button.html(originalContent);
                    }
                }
            });
        }
        
        function softDeleteTransaction(transactionId, button) {
            if (!confirm('Вы уверены, что хотите удалить эту транзакцию?\n\nДанные будут удалены при сохранении формы.')) {
                return;
            }
            
            // Показываем индикатор загрузки
            const originalContent = button.html();
            button.html('⏳').prop('disabled', true);
            
            // AJAX запрос к Django
            $.ajax({
                url: `/admin/investments/project/ajax/soft-delete/${transactionId}/`,
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function(response) {
                    if (response.status === 'success') {
                        const row = button.closest('tr');
                        markRowAsDeleted(row, button);
                        showMessage(response.message, 'warning');
                    } else {
                        showMessage('Ошибка: ' + response.message, 'error');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX Error:', error);
                    showMessage('Ошибка удаления: ' + error, 'error');
                },
                complete: function() {
                    button.prop('disabled', false);
                    if (button.html() === '⏳') {
                        button.html(originalContent);
                    }
                }
            });
        }
        
        function restoreTransaction(row, button) {
            // Восстанавливаем строку
            row.removeClass('deleted-row');
            row.find('td').css({
                'opacity': '1',
                'text-decoration': 'none',
                'background-color': ''
            });
            
            // Включаем поля обратно
            row.find('input, select').not('[name$="-DELETE"], [name$="-ORDER"]').prop('disabled', false);
            
            // Убираем галочку DELETE
            const deleteCheckbox = row.find('input[name$="-DELETE"]');
            if (deleteCheckbox.length > 0) {
                deleteCheckbox.prop('checked', false);
            }
            
            // Восстанавливаем кнопки
            const editBtn = row.find('.django-btn-edit');
            
            editBtn.show();
            button.html('🗑️').attr('title', 'Удалить').removeClass('django-btn-restore').addClass('django-btn-delete');
            
            showMessage('Удаление отменено', 'info');
        }
        
        function makeRowEditable(row) {
            row.find('input[type="text"], input[type="number"], input[type="date"], select').each(function() {
                const field = $(this);
                
                // Пропускаем служебные поля и поля кнопок действий
                if (field.attr('name') && 
                    !field.attr('name').includes('DELETE') && 
                    !field.attr('name').includes('ORDER') &&
                    !field.closest('.transaction-actions').length) {
                    
                    field.prop('readonly', false);
                    field.prop('disabled', false);
                    field.removeClass('readonly-field');
                    field.addClass('editable-field');
                }
            });
            
            row.removeClass('readonly-row').addClass('editable-row');
        }
        
        function makeRowReadonly(row) {
            row.find('input[type="text"], input[type="number"], input[type="date"], select').each(function() {
                const field = $(this);
                
                // Пропускаем служебные поля и поля кнопок действий
                if (field.attr('name') && 
                    !field.attr('name').includes('DELETE') && 
                    !field.attr('name').includes('ORDER') &&
                    !field.closest('.transaction-actions').length) {
                    
                    field.prop('readonly', true);
                    field.removeClass('editable-field');
                    field.addClass('readonly-field');
                }
            });
            
            row.removeClass('editable-row').addClass('readonly-row');
        }
        
        function markRowAsDeleted(row, button) {
            row.addClass('deleted-row');
            
            // Добавляем визуальные эффекты удаления
            row.find('td').css({
                'opacity': '0.6',
                'text-decoration': 'line-through',
                'background-color': '#f8d7da'
            });
            
            // Отключаем все поля
            row.find('input, select').not('[name$="-DELETE"], [name$="-ORDER"]').prop('disabled', true);
            
            // Ищем и отмечаем checkbox DELETE если есть
            const deleteCheckbox = row.find('input[name$="-DELETE"]');
            if (deleteCheckbox.length > 0) {
                deleteCheckbox.prop('checked', true);
            }
            
            // Меняем кнопки
            const editBtn = row.find('.django-btn-edit');
            
            editBtn.hide();
            button.html('↶').attr('title', 'Отменить удаление').removeClass('django-btn-delete').addClass('django-btn-restore');
        }
        
        function setupReadonlyFields() {
            // Изначально делаем все существующие поля readonly
            $('.inline-group table tbody tr').each(function() {
                const row = $(this);
                
                // Пропускаем пустые формы и уже обработанные строки
                if (!row.hasClass('empty-form') && !row.hasClass('readonly-row') && 
                    row.find('input[type="text"], input[type="date"], select').length > 0) {
                    
                    // Проверяем, есть ли данные в строке
                    const hasData = row.find('input[type="text"], input[type="date"], select').filter(function() {
                        return $(this).val() && $(this).val().trim() !== '';
                    }).length > 0;
                    
                    if (hasData) {
                        makeRowReadonly(row);
                    }
                }
            });
        }
        
        function addCalendarButtons() {
            console.log('📅 Добавляем календарные кнопки только для транзакций...');
            
            // Находим ТОЛЬКО поля дат в таблице транзакций
            $('.inline-group table tbody tr').each(function() {
                const row = $(this);
                
                // Пропускаем пустые формы и шаблоны
                if (row.hasClass('empty-form') || row.find('input[name*="__prefix__"]').length > 0) {
                    return;
                }
                
                // Ищем поле даты в этой строке
                const dateField = row.find('input[name*="date"]:not([name*="DELETE"])').first();
                
                if (dateField.length > 0 && dateField.next('.date-shortcuts').length === 0) {
                    // Создаем кнопки
                    const shortcuts = $(`
                        <span class="date-shortcuts" style="margin-left: 5px;">
                            <button type="button" class="today-btn" style="
                                font-size: 10px; padding: 2px 4px; background: #2196F3; 
                                color: white; border: none; border-radius: 2px; margin: 0 1px;
                                cursor: pointer; font-weight: bold;
                            ">T</button>
                            <button type="button" class="cal-btn" style="
                                font-size: 10px; padding: 2px 4px; background: #4CAF50; 
                                color: white; border: none; border-radius: 2px; margin: 0 1px;
                                cursor: pointer; font-weight: bold;
                            ">C</button>
                        </span>
                    `);
                    
                    // Добавляем после поля
                    dateField.after(shortcuts);
                    
                    // Обработчик кнопки Today
                    shortcuts.find('.today-btn').click(function(e) {
                        e.preventDefault();
                        const today = new Date();
                        const dateString = today.getFullYear() + '-' + 
                            String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                            String(today.getDate()).padStart(2, '0');
                        dateField.val(dateString).trigger('change');
                        console.log('📅 Установлена сегодняшняя дата:', dateString);
                    });
                    
                    // Обработчик кнопки Calendar
                    shortcuts.find('.cal-btn').click(function(e) {
                        e.preventDefault();
                        dateField.focus();
                        setTimeout(function() {
                            if (dateField[0].showPicker) {
                                dateField[0].showPicker();
                            } else {
                                dateField[0].click();
                            }
                        }, 100);
                        console.log('📅 Открытие календаря для поля:', dateField.attr('name'));
                    });
                    
                    console.log('📅 Добавлены кнопки для поля транзакции:', dateField.attr('name'));
                }
            });
        }
        
        function getCSRFToken() {
            // Ищем CSRF token в разных местах
            return $('[name=csrfmiddlewaretoken]').val() || 
                   $('meta[name=csrf-token]').attr('content') ||
                   document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                   window.csrf_token;
        }
        
        function showMessage(message, type = 'info') {
            // Удаляем предыдущие сообщения
            $('.django-message').remove();
            
            // Определяем цвета для разных типов сообщений
            const colors = {
                'success': { bg: '#d4edda', border: '#c3e6cb', color: '#155724' },
                'error': { bg: '#f8d7da', border: '#f5c6cb', color: '#721c24' },
                'warning': { bg: '#fff3cd', border: '#ffeaa7', color: '#856404' },
                'info': { bg: '#d1ecf1', border: '#bee5eb', color: '#0c5460' }
            };
            
            const style = colors[type] || colors['info'];
            
            // Создаем сообщение в стиле вашего дизайна
            const messageDiv = $(`
                <div class="django-message" style="
                    position: fixed;
                    top: 120px;
                    right: 20px;
                    z-index: 10000;
                    padding: 12px 20px;
                    border-radius: 6px;
                    background: ${style.bg};
                    border: 1px solid ${style.border};
                    color: ${style.color};
                    max-width: 350px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    font-family: system-ui, -apple-system, Arial, sans-serif;
                    font-size: 13px;
                    line-height: 1.4;
                ">
                    <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${message}
                    <button type="button" style="
                        float: right;
                        background: none;
                        border: none;
                        font-size: 16px;
                        cursor: pointer;
                        color: inherit;
                        margin-left: 10px;
                        margin-top: -2px;
                    " onclick="$(this).parent().fadeOut()">×</button>
                </div>
            `);
            
            $('body').append(messageDiv);
            
            // Автоматическое скрытие через 4 секунды
            setTimeout(function() {
                messageDiv.fadeOut(300, function() {
                    $(this).remove();
                });
            }, 4000);
        }
        
        // Следим за добавлением новых inline форм
        $(document).on('formset:added', function(event) {
            console.log('🔄 Добавлена новая inline форма');
            setTimeout(function() {
                bindActionButtons();
                addCalendarButtons();
            }, 200);
        });
        
        // Предотвращаем случайную отправку формы при клике на кнопки действий
        $(document).on('click.transactionActions', '.django-btn-edit, .django-btn-delete, .django-btn-restore', function(e) {
            e.preventDefault();
            e.stopPropagation();
        });
        
        // Предупреждение о несохраненных изменениях
        let hasUnsavedChanges = false;
        
        $(document).on('input change', '.editable-field', function() {
            hasUnsavedChanges = true;
        });
        
        $(document).on('submit', 'form', function() {
            hasUnsavedChanges = false;
        });
        
        window.addEventListener('beforeunload', function(e) {
            if (hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = 'У вас есть несохраненные изменения. Вы уверены, что хотите покинуть страницу?';
            }
        });
        
        console.log('✅ Система действий для транзакций инициализирована успешно');
        
    });
})(django.jQuery || jQuery);