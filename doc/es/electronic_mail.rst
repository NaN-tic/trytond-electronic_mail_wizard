#:after:electronic_mail/electronic_mail:section:configuracion#

También es posible enviar estos correos de forma manual desde una pantalla en concreto
(por ejemplo,desde *facturas* o *pedidos*), por medio del icono *Ejecutar acción*.


#:after:electronic_mail_template/electronic_mail:paragraph:plantillas#

Podemos marcar también la opción |create_action| para que se nos habilite la posibilidad
de mandar un correo-e por medio del icono *Ejecutar acción*.
Más adelante (:ref:`en esta sección <envio-accion>`) veremos como enviar un correo-e por medio
esta funcionalidad.

.. warning::

   Cuando activemos esta funcionalidad por primera vez deberemos cerrar el cliente
   Tryton y volver a identificarnos para que se haga efectiva. Esto es debido a que
   los botones de la cabecera se encuentran en memoria para ir más rápido en las 
   aperturas de las vistas.


#:after:electronic_mail_template/electronic_mail:section:envio_manual#

.. _envio-accion:

Enviar correo-e por medio de *Ejecutar acción* 
==============================================

Cuando tengamos creada una plantilla y accedamos al menú del modelo sobre el 
que se ha creado, podremos realizar un envío de esta plantilla
de forma manual por medio del botón *Ejecutar acción*. Cuando cliquemos en 
el icono, nos aparecerá una opción con el nombre de la plantilla y dándole se
generará una ventana flotante que actuará de asistente en el envío del 
correo-e. En ella vendrá reflejada la información ya renderizada de la plantilla 
(si dispone de *tags*).

.. Note:: Por ejemplo si en la plantilla tenemos el *tag* "${record.number}" ya 
   nos mostrará en esta ventana el valor según el registro seleccionado. Por 
   ejemplo, si es un número de referencia, nos aparecerá el número de referencia
   correspondiente al registro seleccionado.
   
.. view:: electronic_mail_wizard.templateemail_start

   Vista de la plantilla del correo electrónico

En esta ventana se puede editar el cuerpo del mensaje, la descripción o 
los remitentes. Simplemente propone un formato de correo que podremos editar si 
lo deseamos. Además, en la esquina inferior izquierda nos indicará el total de 
registros seleccionados y, por tanto, el número de correos-e que se enviarán.

Si en vez de seleccionar un registro decidimos seleccionar varios para 
enviar el correo, se enviará un correo para cada uno pero en el contenido del
asistente no se visualizarán los *tags* con la información correspondiente.
En el momento de enviar el correo, los *tags* serán cambiados con la información
de cada registro.

.. Note:: Si edita la información del asistente y añade nuevos *tags*, debe 
   de estar seguro que son correctos, ya que en caso contrario, dará error y el
   correo no se enviará (notificando al administrador).

El último paso será clicar en *Enviar*, y se generará un correo electrónico
a partir de la información que hemos introducido en el asistente por cada 
registro seleccionado.

.. |create_action| field:: electronic.mail.template/create_action
