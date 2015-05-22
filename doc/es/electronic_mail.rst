#:after:electronic_mail/electronic_mail:section:configuracion#

===============================
Asistente de correo electrónico
===============================

Permite relacionar asistentes con plantillas de correo electrónico.

Configuración
=============

Cuando añada una nueva plantilla si marca la opción `Crear Acción` se creará
una acción en el modelo de la plantilla que permite el envío del correo
electrónico para los registros seleccionados.

.. note:: Una vez generado el asistente, para que esté visible, deberemos
          cerrar el cliente GTK y volver a identificarnos. Esto es debido a que
          los botones de la cabezera se encuentran en memória para ir más
          rápido en las aperturas de las vistas.

Si selecciona un solo registro, se mostrarà la previsualización previa del
correo a enviar que podrà modificar. Si se selecciona mas de un registro se
mostrará una previsualización del correo, con los campos de la plantilla que se
evaluarán para cada registro.

Envío correo
============

Cuando seleccione un registro, dispone de un asistente para enviar el correo que convertirá
los datos de la plantilla con la información ya renderizada (si dispone de tags). Por ejemplo si 
en la plantilla tenemos el tag "${record.number}" ya nos mostrará en el asistente el valor según el registro
seleccionado, por ejemplo al ser un número de referencia, "V123456".

En el asistente podrá editar el cuerpo del mensaje, como la descripción o remitentes. Simplemente
propone un formato de correo que posteriormente lo podrá editar si lo desea.

El último paso del asistente será enviar, y se generará un correo electrónico a partir de la información
que hemos introducido en el asistente. No generará un correo a partir de la plantilla, si no del asistente.

Si en vez de seleccionar un registro decide seleccionar varios registros para enviar el correo, se enviará
un correo para cada uno pero el contenido del asistente no se visualizará los tags con los información correspondiente.
En el momento de enviar el correo, los tags serán canviados con la información del registro. Si edita la información
del asistente y añade nuevos tags, debe de estar seguro que son correctos, ya que en caso contrario, dará error y
el correo no se enviará (notificando al administrador).
