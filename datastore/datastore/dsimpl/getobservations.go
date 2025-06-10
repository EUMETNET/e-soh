package dsimpl

import (
	"context"
	"fmt"

	"datastore/common"
	"datastore/datastore"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (svcInfo *ServiceInfo) GetObservations(
	ctx context.Context, request *datastore.GetObsRequest) (
	*datastore.GetObsResponse, error) {

	tspec, err := common.GetTemporalSpec(request.GetTemporalLatest(), request.GetTemporalInterval())
	if err != nil {
		return nil, status.Error(
			codes.Internal, fmt.Sprintf("common.GetTemporalSpec() failed: %v", err))
	}

	response, errCode, reason := svcInfo.Sbe.GetObservations(request, tspec)
	if errCode != codes.OK {
		return nil, status.Error(
			errCode, fmt.Sprintf("svcInfo.Sbe.GetObservations() failed: %s", reason))
	}

	return response, nil
}
