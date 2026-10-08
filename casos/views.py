from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from datetime import date
from .models import Cliente, Caso, EstadoCaso, Expediente, Pago

# --- MANTENEDOR WEB DE CLIENTES ---
def lista_clientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'casos/lista_clientes.html', {'clientes': clientes})

def crear_cliente(request):
    if request.method == 'POST':
        Cliente.objects.create(
            nombres=request.POST['nombres'],
            documento=request.POST['documento'],
            telefono=request.POST['telefono'],
            correo=request.POST['correo']
        )
        return redirect('lista_clientes')
    return render(request, 'casos/form_cliente.html')

def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, pk=id)
    if request.method == 'POST':
        cliente.nombres = request.POST['nombres']
        cliente.documento = request.POST['documento']
        cliente.telefono = request.POST['telefono']
        cliente.correo = request.POST['correo']
        cliente.save()
        return redirect('lista_clientes')
    return render(request, 'casos/form_cliente.html', {'cliente': cliente})

def eliminar_cliente(request, id):
    cliente = get_object_or_404(Cliente, pk=id)
    if request.method == 'POST':
        cliente.delete()
        return redirect('lista_clientes')
    return render(request, 'casos/eliminar_cliente.html', {'cliente': cliente})

# --- VISTAS DE CASOS, COOKIES Y REGISTRO DE PAGOS ---
def lista_casos(request):
    estado_id = request.GET.get('estado')
    
    # 3. Manejo de Cookie para recordar el último estado consultado
    if not estado_id:
        estado_id = request.COOKIES.get('ultimo_estado')

    if estado_id:
        casos = Caso.objects.filter(estado_id=estado_id)
    else:
        casos = Caso.objects.all()

    estados = EstadoCaso.objects.all()
    response = render(request, 'casos/lista_casos.html', {
        'casos': casos,
        'estados': estados,
        'estado_seleccionado': estado_id
    })

    # Guardar en Cookie si vino por request.GET
    if request.GET.get('estado'):
        response.set_cookie('ultimo_estado', request.GET.get('estado'), max_age=3600*24)

    return response

def detalle_caso(request, id):
    caso = get_object_or_404(Caso, pk=id)
    error = None

    # 1. Registro de Pago por POST con validación de estado
    if request.method == 'POST':
        monto = request.POST.get('monto')
        descripcion = request.POST.get('descripcion')
        try:
            pago = Pago(caso=caso, monto=monto, fecha=date.today(), descripcion=descripcion)
            pago.clean()  # Lanza ValidationError si el estado no permite pagos
            pago.save()
            return redirect('detalle_caso', id=caso.id)
        except ValidationError as e:
            error = e.message

    return render(request, 'casos/detalle_caso.html', {'caso': caso, 'error': error})

# 2. Vista para subir documentos a expedientes por request.FILES
def subir_documento(request, id):
    caso = get_object_or_404(Caso, pk=id)
    if request.method == 'POST' and request.FILES.get('documento'):
        expediente_id = request.POST.get('expediente_id')
        expediente = get_object_or_404(Expediente, pk=expediente_id, caso=caso)
        expediente.documento = request.FILES['documento']
        expediente.save()
    return redirect('detalle_caso', id=caso.id)

# 4. Vista API JSON de un Caso
def api_caso(request, id):
    caso = get_object_or_404(Caso, pk=id)
    abogados_lista = [
        abg.usuario.get_full_name() or abg.usuario.username 
        for abg in caso.abogados.all()
    ]
    data = {
        'codigo': caso.codigo,
        'cliente': caso.cliente.nombres,
        'estado': caso.estado.nombre,
        'abogados': abogados_lista,
        'numero_expedientes': caso.expedientes.count(),
        'total_pagado': float(caso.total_pagado())
    }
    return JsonResponse(data)